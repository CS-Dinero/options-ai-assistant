"""
engines/strategy_regime.py
Volatility + Gamma Alignment (VGA) environment classifier.

Combines IV regime, gamma regime, and expected move position into
a single decision label that tells strategies which market environment
they are operating in.

VGA environments:
    premium_selling      — positive gamma + elevated/rich IV
                           → credit spreads, iron condors
    neutral_time_spreads — positive gamma + cheap/moderate IV
                           → calendars, time spreads
    cautious_directional — negative gamma + price near gamma flip
                           → reduced size debit spreads, careful diagonals
    trend_directional    — negative gamma + price away from flip
                           → full-size debit spreads, diagonals
    mixed                — insufficient data or ambiguous signals

Design rule: deterministic and fast. No external calls.
"""

from __future__ import annotations


# VGA environment labels — use these strings everywhere
VGA_PREMIUM_SELLING      = "premium_selling"
VGA_TIME_SPREADS         = "neutral_time_spreads"
VGA_CAUTIOUS_DIRECTIONAL = "cautious_directional"
VGA_TREND_DIRECTIONAL    = "trend_directional"
VGA_MIXED                = "mixed"

ALL_VGA_ENVIRONMENTS = (
    VGA_PREMIUM_SELLING,
    VGA_TIME_SPREADS,
    VGA_CAUTIOUS_DIRECTIONAL,
    VGA_TREND_DIRECTIONAL,
    VGA_MIXED,
)

# Strategy families that perform best in each environment
VGA_STRATEGY_PREFERENCES: dict[str, list[str]] = {
    VGA_PREMIUM_SELLING:      ["bull_put", "bear_call"],
    VGA_TIME_SPREADS:         ["calendar"],
    VGA_CAUTIOUS_DIRECTIONAL: ["bull_call_debit", "bear_put_debit"],
    VGA_TREND_DIRECTIONAL:    ["bull_call_debit", "bear_put_debit", "diagonal"],
    VGA_MIXED:                [],
}


def determine_vga_environment(
    gamma_regime: str | None,
    iv_regime: str | None,
    spot_price: float | None = None,
    expected_move: float | None = None,
    gamma_flip: float | None = None,
) -> str:
    """
    Classify the current market environment into a VGA label.

    Rules:
        Positive gamma + elevated/rich IV   → premium_selling
        Positive gamma + cheap/moderate IV  → neutral_time_spreads
        Negative gamma + near flip          → cautious_directional
        Negative gamma + away from flip     → trend_directional
        Any missing critical input          → mixed

    Returns one of the five VGA_* constants.
    """
    if not gamma_regime or not iv_regime:
        return VGA_MIXED

    if gamma_regime == "positive":
        if iv_regime in ("elevated", "rich"):
            return VGA_PREMIUM_SELLING
        if iv_regime in ("cheap", "moderate"):
            return VGA_TIME_SPREADS
        # elevated/neutral/unknown — treat as mixed
        return VGA_MIXED

    if gamma_regime == "negative":
        # Use proximity to gamma flip to gauge directional conviction
        if (spot_price is not None and expected_move is not None
                and gamma_flip is not None and expected_move > 0):
            distance_to_flip = abs(spot_price - gamma_flip)
            if distance_to_flip <= expected_move:
                return VGA_CAUTIOUS_DIRECTIONAL
            return VGA_TREND_DIRECTIONAL
        # Gamma negative but flip unknown — conservative
        return VGA_CAUTIOUS_DIRECTIONAL

    # neutral gamma or unknown
    return VGA_MIXED


def determine_vga_from_context(context: dict) -> str:
    """
    Convenience wrapper — extract fields from a derived context dict
    and return the VGA environment label.

    Compatible with both live derived context and backtest daily context.
    """
    return determine_vga_environment(
        gamma_regime  = context.get("gamma_regime"),
        iv_regime     = context.get("iv_regime"),
        spot_price    = context.get("spot_price"),
        expected_move = context.get("expected_move"),
        gamma_flip    = context.get("gamma_flip"),
    )


def vga_strategy_scores(vga_environment: str, strategy_type: str) -> float:
    """
    Return a scoring multiplier for a strategy given the VGA environment.

    Used by trade_scoring.py to boost or penalize strategies based on
    environment alignment.

    Returns:
        1.0  — ideal environment for this strategy
        0.70 — acceptable environment
        0.40 — poor environment (strategy penalized)
    """
    preferred = VGA_STRATEGY_PREFERENCES.get(vga_environment, [])

    if strategy_type in preferred:
        return 1.0

    # Partial credit for broadly compatible strategies
    broad_credit = {
        VGA_PREMIUM_SELLING:      {"calendar": 0.70, "diagonal": 0.50,
                                    "bull_call_debit": 0.50, "bear_put_debit": 0.50},
        VGA_TIME_SPREADS:         {"bull_put": 0.70, "bear_call": 0.70,
                                    "diagonal": 0.80},
        VGA_CAUTIOUS_DIRECTIONAL: {"bull_put": 0.60, "bear_call": 0.60,
                                    "diagonal": 0.70},
        VGA_TREND_DIRECTIONAL:    {"bull_put": 0.50, "bear_call": 0.50,
                                    "calendar": 0.40},
        VGA_MIXED:                {},
    }

    partial = broad_credit.get(vga_environment, {})
    return partial.get(strategy_type, 0.40)
