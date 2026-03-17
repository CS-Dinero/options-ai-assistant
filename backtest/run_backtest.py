"""
backtest/run_backtest.py
Phase 4 backtest orchestrator.

Reuses all live strategy modules — no duplicate logic here.
Pipeline:
  1. load historical data
  2. build daily contexts + VGA environment labels
  3. generate candidates using live strategy modules
  4. filter to top trade(s) per day
  5. simulate trade lifecycles
  6. build equity curve
  7. compute performance metrics
  8. generate segmented reports
  9. validate all outputs
  10. return normalized result bundle

MVP scope: SPY, spreads only, 1 trade per day.
"""

from __future__ import annotations

from backtest.data_loader      import (load_price_history, load_option_chain_history,
                                        load_volatility_history, load_gex_history,
                                        build_historical_market_snapshot)
from backtest.signal_builder   import build_context_series
from backtest.trade_simulator  import simulate_trade
from backtest.portfolio_engine import compute_equity_curve, summarize_equity_curve
from backtest.performance      import summarize_performance
from backtest.reports          import (summarize_by_strategy, summarize_by_environment,
                                        summarize_by_symbol, summarize_by_regime)
from backtest.validation       import (validate_contexts, validate_simulated_trades,
                                        validate_equity_curve, validate_reports,
                                        combine_validation_results, all_checks_pass)

from strategies.bear_call      import generate_bear_call_spreads
from strategies.bull_put       import generate_bull_put_spreads
from strategies.bull_call_debit import generate_bull_call_debit_spreads
from strategies.bear_put_debit import generate_bear_put_debit_spreads


# ─────────────────────────────────────────────
# CANDIDATE GENERATION
# ─────────────────────────────────────────────

def generate_trade_candidates_for_date(
    date_str: str,
    context:  dict,
    chain:    list[dict],
) -> list[dict]:
    """
    Generate all strategy candidates for one historical date using live modules.

    Builds a minimal market dict from context, then calls each generator.
    This ensures backtest uses exactly the same logic as the live dashboard.
    """
    market = {
        "symbol":               context["symbol"],
        "spot_price":           context["spot_price"],
        "short_dte_target":     7,
        "long_dte_target":      60,
        "default_spread_width": 5,
        "preferred_risk_dollars": 500,
        # Forward IV fields for expected move
        "atm_call_mid":  None,  # will be computed from chain in context
        "atm_put_mid":   None,
        "front_iv":      context.get("front_iv"),
        "back_iv":       context.get("back_iv"),
        "front_dte":     7,
    }

    derived = context   # context already has all derived fields incl. VGA

    candidates: list[dict] = []
    try:
        candidates += generate_bear_call_spreads(market, chain, derived)
    except Exception:
        pass
    try:
        candidates += generate_bull_put_spreads(market, chain, derived)
    except Exception:
        pass
    try:
        candidates += generate_bull_call_debit_spreads(market, chain, derived)
    except Exception:
        pass
    try:
        candidates += generate_bear_put_debit_spreads(market, chain, derived)
    except Exception:
        pass

    return candidates


def filter_candidates_for_backtest(
    candidates: list[dict],
    max_trades_per_day: int = 1,
    score_threshold: int = 65,
) -> list[dict]:
    """
    Select top N candidates by score, filtered by minimum score threshold.
    MVP: take only the top-scoring trade per day.
    """
    qualified = [c for c in candidates if c.get("confidence_score", 0) >= score_threshold]
    ranked    = sorted(qualified, key=lambda x: x.get("confidence_score", 0), reverse=True)
    return ranked[:max_trades_per_day]


def prepare_trade_for_simulation(
    candidate:   dict,
    date_str:    str,
    context:     dict,
    trade_index: int,
) -> dict:
    """
    Augment a strategy candidate with backtest metadata.
    Returns a trade dict ready for simulate_trade().
    """
    trade = dict(candidate)
    trade["trade_id"]        = f"{context['symbol']}_{date_str}_{candidate['strategy_type']}_{trade_index}"
    trade["entry_date"]      = date_str
    trade["vga_environment"] = context.get("vga_environment")
    trade["iv_regime"]       = context.get("iv_regime")
    trade["gamma_regime"]    = context.get("gamma_regime")
    trade["term_structure"]  = context.get("term_structure")
    trade["score"]           = candidate.get("confidence_score", 0)
    return trade


# ─────────────────────────────────────────────
# RETURN SERIES
# ─────────────────────────────────────────────

def build_return_series(equity_curve: list[dict]) -> list[float]:
    """Convert equity curve into daily return ratios for Sharpe/Sortino."""
    returns: list[float] = []
    for i in range(1, len(equity_curve)):
        prev = equity_curve[i - 1]["equity"]
        curr = equity_curve[i]["equity"]
        returns.append((curr - prev) / prev if prev != 0 else 0.0)
    return returns


# ─────────────────────────────────────────────
# MAIN ORCHESTRATOR
# ─────────────────────────────────────────────

def run_backtest(
    symbols:            list[str],
    start:              str,
    end:                str,
    starting_capital:   float = 100_000.0,
    max_trades_per_day: int   = 1,
    score_threshold:    int   = 65,
) -> dict:
    """
    Run Phase 4 backtest over one or more symbols and a date range.

    Returns a result bundle with:
      simulated_trades, equity_curve, returns,
      performance, reports, equity_summary, validation
    """
    all_contexts         : list[dict] = []
    all_prepared_trades  : list[dict] = []
    all_simulated_trades : list[dict] = []

    for symbol in symbols:
        # ── 1. Load historical data ───────────────────────────────────────────
        price_history = load_price_history(symbol, start, end)
        chain_history = load_option_chain_history(symbol, start, end)
        vol_history   = load_volatility_history(symbol, start, end)
        gex_history   = load_gex_history(symbol, start, end)

        # ── 2. Build merged market snapshots ─────────────────────────────────
        historical_market = build_historical_market_snapshot(
            price_history, vol_history, gex_history, symbol=symbol
        )

        # ── 3. Build context series with VGA labels ───────────────────────────
        contexts = build_context_series(symbol, historical_market, chain_history)
        all_contexts.extend(contexts)

        # ── 4. Generate + filter candidates per day ───────────────────────────
        for context in contexts:
            date_str       = context["date"]
            chain_snapshot = chain_history.get(date_str, [])
            if not chain_snapshot:
                continue

            candidates = generate_trade_candidates_for_date(date_str, context, chain_snapshot)
            selected   = filter_candidates_for_backtest(candidates, max_trades_per_day, score_threshold)

            for idx, candidate in enumerate(selected, start=1):
                trade = prepare_trade_for_simulation(candidate, date_str, context, idx)
                all_prepared_trades.append(trade)

        # ── 5. Simulate trades ────────────────────────────────────────────────
        for trade in all_prepared_trades:
            result = simulate_trade(trade, chain_history, price_history)
            all_simulated_trades.append(result)

    # ── 6. Build equity curve ─────────────────────────────────────────────────
    equity_curve   = compute_equity_curve(all_simulated_trades, starting_capital)
    equity_summary = summarize_equity_curve(equity_curve, starting_capital)

    # ── 7. Return series ──────────────────────────────────────────────────────
    returns = build_return_series(equity_curve)

    # ── 8. Performance ────────────────────────────────────────────────────────
    performance = summarize_performance(all_simulated_trades, equity_curve, returns)

    # ── 9. Reports ────────────────────────────────────────────────────────────
    reports = {
        "by_strategy":    summarize_by_strategy(all_simulated_trades),
        "by_environment": summarize_by_environment(all_simulated_trades),
        "by_symbol":      summarize_by_symbol(all_simulated_trades),
        "by_regime":      summarize_by_regime(all_simulated_trades),
    }

    # ── 10. Validate ──────────────────────────────────────────────────────────
    validation = combine_validation_results(
        validate_contexts(all_contexts),
        validate_simulated_trades(all_simulated_trades) if all_simulated_trades else [],
        validate_equity_curve(equity_curve, equity_summary) if equity_curve else [],
        validate_reports(reports),
    )

    return {
        "simulated_trades": all_simulated_trades,
        "equity_curve":     equity_curve,
        "equity_summary":   equity_summary,
        "returns":          returns,
        "performance":      performance,
        "reports":          reports,
        "validation":       validation,
        "passed":           all_checks_pass(validation) if all_simulated_trades else None,
    }
