"""
backtest/signal_builder.py
Reconstructs daily derived context for historical backtesting.

Reuses the same live engines used by context_builder.py, ensuring
the backtest validates exactly the same logic the live engine runs.

Key outputs per day:
  - expected move, upper/lower EM
  - IV regime, IV rank
  - term structure, skew
  - gamma regime, gamma flip, gamma trap (real GEX from chain)
  - VGA environment label

This is the most critical Phase 4 file — if context reconstruction
is wrong, all downstream results are misleading.
"""

from __future__ import annotations

from engines.expected_move  import compute_expected_move
from engines.atr_engine     import classify_atr_trend, em_atr_ratio
from engines.iv_regime      import classify_iv_regime, compute_iv_rank
from engines.term_structure import compute_term_slope, classify_term_structure
from engines.skew_engine    import compute_skew, classify_skew
from engines.gamma_engine   import (
    aggregate_gex_by_strike,
    compute_total_gex,
    estimate_gamma_flip,
    identify_gamma_trap,
    classify_gamma_regime,
)
from engines.strategy_regime import determine_vga_from_context
from calculator.chain_helpers import nearest_atm


def build_daily_context(date: str, market: dict, chain: list[dict]) -> dict:
    """
    Build one day's full derived context from historical market + chain data.

    Mirrors the live build_derived() in engines/context_builder.py but
    also accepts a date string for backtest labeling.

    All inputs are None-safe — missing data produces 'unknown' regimes.
    """
    symbol     = market.get("symbol", "SPY")
    spot_price = market.get("spot_price", 0.0)
    short_dte  = market.get("short_dte_target", 7)

    # ── Expected move ─────────────────────────────────────────────────────────
    atm_call = nearest_atm(chain, "call", short_dte, spot_price) if chain else None
    atm_put  = nearest_atm(chain, "put",  short_dte, spot_price) if chain else None

    em_result = compute_expected_move(
        spot         = spot_price,
        atm_call_mid = atm_call["mid"] if atm_call else None,
        atm_put_mid  = atm_put["mid"]  if atm_put  else None,
        iv_percent   = market.get("front_iv"),
        dte          = short_dte,
    )

    # ── ATR regime ────────────────────────────────────────────────────────────
    atr_14    = market.get("atr_14")
    atr_prior = market.get("atr_prior")
    atr_trend = (classify_atr_trend(atr_14, atr_prior)
                 if atr_14 is not None and atr_prior is not None else None)
    em_ratio  = (em_atr_ratio(em_result["expected_move"], atr_14)
                 if atr_14 is not None else None)

    # ── IV regime ─────────────────────────────────────────────────────────────
    front_iv      = market.get("front_iv")
    back_iv       = market.get("back_iv")
    iv_percentile = market.get("iv_percentile")
    iv_rank       = compute_iv_rank(front_iv, market.get("iv_min"), market.get("iv_max"))
    iv_regime     = classify_iv_regime(iv_percentile) if iv_percentile is not None else None

    # ── Term structure ────────────────────────────────────────────────────────
    term_slope = (compute_term_slope(front_iv, back_iv)
                  if front_iv is not None and back_iv is not None else None)
    term_structure = (classify_term_structure(term_slope)
                      if term_slope is not None else "unknown")

    # ── Skew ─────────────────────────────────────────────────────────────────
    put_25d_iv  = market.get("put_25d_iv")
    call_25d_iv = market.get("call_25d_iv")
    skew_value  = (compute_skew(put_25d_iv, call_25d_iv)
                   if put_25d_iv is not None and call_25d_iv is not None else None)
    skew_state  = classify_skew(skew_value) if skew_value is not None else "unknown"

    # ── Real gamma engine (from historical chain) ─────────────────────────────
    gex_by_strike = aggregate_gex_by_strike(chain, spot_price) if chain else {}
    total_gex     = compute_total_gex(gex_by_strike)
    gamma_flip    = estimate_gamma_flip(gex_by_strike)
    gamma_trap    = identify_gamma_trap(gex_by_strike)
    gamma_regime  = classify_gamma_regime(total_gex)

    context = {
        "date":   date,
        "symbol": symbol,

        # Expected move
        "spot_price":    spot_price,
        "expected_move": em_result["expected_move"],
        "upper_em":      em_result["upper_em"],
        "lower_em":      em_result["lower_em"],
        "em_method":     em_result["method"],

        # ATR
        "atr_14":       atr_14,
        "atr_trend":    atr_trend,
        "em_atr_ratio": em_ratio,

        # IV
        "front_iv":      front_iv,
        "back_iv":       back_iv,
        "iv_percentile": iv_percentile,
        "iv_rank":       iv_rank,
        "iv_regime":     iv_regime,

        # Term structure
        "term_slope":     term_slope,
        "term_structure": term_structure,

        # Skew
        "skew_value": skew_value,
        "skew_state": skew_state,

        # Gamma
        "gex_by_strike": gex_by_strike,
        "total_gex":     total_gex,
        "gamma_regime":  gamma_regime,
        "gamma_flip":    gamma_flip,
        "gamma_trap":    gamma_trap,
    }

    # VGA environment — computed last so all inputs are available
    context["vga_environment"] = determine_vga_from_context(context)
    return context


def determine_vga_environment(context: dict) -> str:
    """Convenience wrapper for external callers."""
    return determine_vga_from_context(context)


def build_context_series(
    symbol:             str,
    historical_market:  dict[str, dict],
    chain_history:      dict[str, list[dict]],
) -> list[dict]:
    """
    Build a time-ordered list of daily contexts.

    Only builds a context for dates where both a market snapshot
    and a chain snapshot are available.

    Returns list of DailyContext dicts sorted by date.
    """
    contexts: list[dict] = []

    all_dates = sorted(
        d for d in historical_market.keys()
        if d in chain_history and chain_history[d]
    )

    for date_str in all_dates:
        market_snap = historical_market[date_str]
        chain_snap  = chain_history[date_str]

        try:
            context = build_daily_context(date_str, market_snap, chain_snap)
            contexts.append(context)
        except Exception as e:
            # Skip bad dates — don't crash the whole backtest
            continue

    return contexts
