"""
engines/context_builder.py
Builds the full derived analytics context from market + chain data.

Centralized here so main.py, dashboard/app.py, and validation/checks.py
can all import from this module without circular dependencies.

This is the single source of truth for derived context construction.
"""

from engines.expected_move  import compute_expected_move
from engines.atr_engine     import classify_atr_trend, em_atr_ratio
from engines.iv_regime      import classify_iv_regime
from engines.term_structure import compute_term_slope, classify_term_structure
from engines.skew_engine    import compute_skew, classify_skew
from engines.gamma_engine   import compute_gamma_context, classify_gamma_regime


def build_derived(market: dict, chain: list | None = None) -> dict:
    """
    Compute all derived analytics from market context + live chain data.

    Args:
        market  — market context dict (spot, IV, ATR, skew inputs, etc.)
        chain   — option chain rows for real GEX computation.
                  If None, falls back to market placeholder values.

    Returns a flat dict consumed by strategies, scoring, and dashboard.
    All values are None-safe — missing inputs produce 'unknown' states
    which the scorer handles via proportional weight redistribution.
    """
    em_result = compute_expected_move(
        spot         = market["spot_price"],
        atm_call_mid = market.get("atm_call_mid"),
        atm_put_mid  = market.get("atm_put_mid"),
        iv_percent   = market.get("front_iv", 16.0),
        dte          = market.get("front_dte", 7),
    )

    term_slope = compute_term_slope(
        market.get("front_iv", 16.0),
        market.get("back_iv",  16.0),
    )
    skew_val = compute_skew(
        market.get("put_25d_iv"),
        market.get("call_25d_iv"),
    )

    # ── Real gamma engine ─────────────────────────────────────────────────────
    if chain:
        gamma_ctx = compute_gamma_context(chain, market["spot_price"])
    else:
        # Fallback: use market placeholders (live adapters set these to None)
        total_gex = market.get("total_gex")
        gamma_ctx = {
            "gex_by_strike": {},
            "total_gex":     total_gex,
            "gamma_flip":    market.get("gamma_flip"),
            "gamma_trap":    market.get("gamma_trap_strike"),
            "gamma_regime":  classify_gamma_regime(total_gex),
        }

    return {
        # Expected move
        "expected_move": em_result["expected_move"],
        "upper_em":      em_result["upper_em"],
        "lower_em":      em_result["lower_em"],
        "em_method":     em_result["method"],

        # Regime classifiers
        "atr_trend":      classify_atr_trend(
                              market.get("atr_14", 3.0),
                              market.get("atr_prior", 3.0),
                          ),
        "iv_regime":      classify_iv_regime(market.get("iv_percentile", 50.0)),
        "term_slope":     term_slope,
        "term_structure": classify_term_structure(term_slope),
        "skew_value":     skew_val,
        "skew_state":     classify_skew(skew_val),
        "em_atr_ratio":   em_atr_ratio(
                              em_result["expected_move"],
                              market.get("atr_14", 3.0),
                          ),

        # Real gamma outputs
        "gamma_regime":  gamma_ctx["gamma_regime"],
        "total_gex":     gamma_ctx["total_gex"],
        "gamma_flip":    gamma_ctx["gamma_flip"],
        "gamma_trap":    gamma_ctx["gamma_trap"],
        "gex_by_strike": gamma_ctx["gex_by_strike"],
    }
