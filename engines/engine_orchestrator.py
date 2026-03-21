"""
engines/engine_orchestrator.py
Single entry point for the Options AI Assistant engine.

One call returns everything the dashboard needs:
  - vga_environment
  - ranked trade candidates
  - contract sizing
  - position management signals

Usage:
    result = run_options_engine(market, chain, derived=None, open_positions=[])
    # result["candidates"]   → ranked trade list
    # result["vga"]          → VGA environment string
    # result["positions"]    → position snapshot with signals
    # result["summary"]      → top-line metrics

The orchestrator never imports dashboard code — it is pure engine.
"""
from __future__ import annotations
from typing import Any


def run_options_engine(
    market:         dict[str, Any],
    chain:          list[dict[str, Any]],
    derived:        dict[str, Any] | None = None,
    open_positions: list[dict[str, Any]] | None = None,
    risk_dollars:   float | None = None,
) -> dict[str, Any]:
    """
    Full engine pass — from raw market + chain to ranked candidates + signals.

    Parameters
    ----------
    market:
        Normalized market dict (output of adapters/report_adapter.py or
        engines/context_builder.py pipeline).
    chain:
        Normalized option chain rows (output of adapters/chain_adapter.py).
    derived:
        Pre-computed derived context dict. If None, build_derived() is called.
    open_positions:
        List of open position dicts (trade_log rows or adapter output).
        If None, position tracker reads from logs/trade_log.csv.
    risk_dollars:
        Override for preferred_risk_dollars. Defaults to market value or 500.

    Returns
    -------
    {
        "vga":          str              — VGA environment label
        "candidates":   list[dict]       — ranked trade candidates (scored)
        "positions":    dict             — position tracker snapshot
        "summary":      dict             — top-line counts + key metrics
        "derived":      dict             — full derived context
        "market":       dict             — normalized market (passthrough)
    }
    """
    # ── 1. Build derived context ───────────────────────────────────────────────
    if derived is None:
        from engines.context_builder import build_derived
        derived = build_derived(market, chain)

    vga = derived.get("vga_environment", "mixed")

    # ── 1b. Regime classification ──────────────────────────────────────────────
    from engines.regime_router import classify_regime, adjust_score_for_regime
    regime = classify_regime(derived)

    # ── 2. Generate and rank candidates ───────────────────────────────────────
    from strategies.bear_call      import generate_bear_call_spreads
    from strategies.bull_put       import generate_bull_put_spreads
    from strategies.bull_call_debit import generate_bull_call_debit_spreads
    from strategies.bear_put_debit  import generate_bear_put_debit_spreads
    from strategies.calendar        import generate_calendar_candidates
    from strategies.diagonal        import generate_diagonal_candidates
    from strategies.double_diagonal import generate_double_diagonal_candidates

    candidates: list[dict] = []
    for gen in [
        generate_bear_call_spreads,
        generate_bull_put_spreads,
        generate_bull_call_debit_spreads,
        generate_bear_put_debit_spreads,
        generate_calendar_candidates,
        generate_diagonal_candidates,
        generate_double_diagonal_candidates,
    ]:
        try:
            candidates.extend(gen(market, chain, derived))
        except Exception:
            pass

    candidates.sort(key=lambda c: c.get("confidence_score", 0), reverse=True)

    # ── 2b. Regime-aware score adjustment and filtering ────────────────────────
    adjusted = []
    for c in candidates:
        st_type = c.get("strategy_type", "")
        if not regime.strategy_allowed(st_type):
            continue
        c["confidence_score"] = adjust_score_for_regime(
            c.get("confidence_score", 0), st_type, regime
        )
        adjusted.append(c)
    candidates = sorted(adjusted, key=lambda c: c.get("confidence_score", 0), reverse=True)

    # ── 3. Apply contract sizing ───────────────────────────────────────────────
    from calculator.risk_engine import compute_contracts
    budget = risk_dollars or market.get("preferred_risk_dollars", 500)
    for c in candidates:
        if c.get("contracts", 0) == 0:
            c["contracts"] = compute_contracts(budget, c.get("max_loss", 0))

    # ── 4. Position snapshot ───────────────────────────────────────────────────
    from position_manager.position_tracker import PositionTracker
    tracker  = PositionTracker()
    snapshot = tracker.snapshot(derived=derived, spot=market.get("spot_price", 0))

    # If caller passed in positions explicitly, inject them as supplemental
    if open_positions:
        snapshot["_injected_positions"] = open_positions

    # ── 5. Summary ────────────────────────────────────────────────────────────
    from config.settings import SCORE_STRONG, SCORE_TRADABLE
    strong   = [c for c in candidates if c.get("confidence_score", 0) >= SCORE_STRONG]
    tradable = [c for c in candidates
                if SCORE_TRADABLE <= c.get("confidence_score", 0) < SCORE_STRONG]

    summary = {
        "vga_environment":    vga,
        "total_candidates":   len(candidates),
        "strong_count":       len(strong),
        "tradable_count":     len(tradable),
        "top_score":          candidates[0].get("confidence_score", 0) if candidates else 0,
        "top_strategy":       candidates[0].get("strategy_type", "") if candidates else "",
        "open_positions":     snapshot["total_open"],
        "high_urgency":       snapshot["summary"]["high_urgency"],
        "gamma_regime":       derived.get("gamma_regime", ""),
        "iv_regime":          derived.get("iv_regime", ""),
        "expected_move":      derived.get("expected_move", 0),
        "spot_price":         market.get("spot_price", 0),
    }

    return {
        "vga":        vga,
        "candidates": candidates,
        "positions":  snapshot,
        "summary":    summary,
        "derived":    derived,
        "market":     market,
        "regime":     regime.to_dict(),
    }
