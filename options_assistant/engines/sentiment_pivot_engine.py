"""
engines/sentiment_pivot_engine.py
Flip recommendation engine — decides whether to stay in current structure or pivot.

Rules (hard-coded, operator-tunable via vh_config.py):
  - Only suggest put diagonals when gamma regime is negative
  - Only suggest call calendars when sentiment flips bullish AND put skew collapses
  - Never pivot if the resulting roll would be a debit
  - Flip suggestions are advisory only — Python decides, LLM explains
"""
from __future__ import annotations

from typing import Any, Literal

from config.vh_config import (
    SENTIMENT_BULLISH_THRESHOLD, SENTIMENT_BEARISH_THRESHOLD,
)

PivotRecommendation = Literal[
    "HOLD_STRUCTURE",
    "PIVOT_TO_CALLS",
    "PIVOT_TO_PUTS",
    "PIVOT_TO_DIAGONAL",
]


def _sf(v: Any, d: float = 0.0) -> float:
    try:
        return float(v) if v not in (None, "", "—") else d
    except (TypeError, ValueError):
        return d


def calculate_pivot_score(
    sentiment_score: float,
    skew_score:      float,
    gamma_regime:    str,
) -> float:
    """
    Compute a normalized pivot score in [-1.0, +1.0].

    Positive → calls/bullish structures favored.
    Negative → puts/bearish structures favored.
    Near zero → no clear directional edge.
    """
    # Base from sentiment
    score = sentiment_score * 0.50

    # Skew adjustment: high put skew → bearish lean, low put skew → bullish lean
    # skew_score > 0 = elevated put IV relative to calls → bearish
    score -= skew_score * 0.30

    # Gamma regime adjustment
    if gamma_regime in ("negative", "NEGATIVE"):
        score -= 0.20   # negative gamma → trend environment → favor directional diagonals
    elif gamma_regime in ("positive", "POSITIVE"):
        score += 0.10   # positive gamma → range-bound → time spread edge

    return round(max(-1.0, min(1.0, score)), 4)


def recommend_sentiment_pivot(
    position:         dict[str, Any],
    market_ctx:       dict[str, Any],
    sentiment_score:  float = 0.0,
    roll_is_credit:   bool  = True,
) -> dict[str, Any]:
    """
    Evaluate whether a structure pivot is warranted.

    Returns a dict with:
      pivot_recommendation  — PivotRecommendation label
      pivot_score           — [-1, +1] composite
      confidence            — LOW / MEDIUM / HIGH
      rationale             — plain-English reason
      allowed               — bool (False if pivot would produce a debit)
    """
    gamma    = str(market_ctx.get("gamma_regime", "")).lower()
    skew     = str(market_ctx.get("skew_regime", "")).lower()
    iv       = str(market_ctx.get("iv_regime", "")).lower()
    struct   = str(position.get("strategy_type", "calendar")).lower()
    opt_side = str(position.get("option_side", position.get("option_type", "call"))).lower()

    # Skew score: positive = elevated put skew, negative = elevated call skew
    put_iv   = _sf(market_ctx.get("put_25d_iv"))
    call_iv  = _sf(market_ctx.get("call_25d_iv"))
    skew_num = round(put_iv - call_iv, 4) if (put_iv and call_iv) else 0.0

    pivot_score = calculate_pivot_score(sentiment_score, skew_num, gamma)

    # ── Decision logic ────────────────────────────────────────────────────────

    # Gating rule: no pivot if roll is a debit
    if not roll_is_credit:
        return {
            "pivot_recommendation": "HOLD_STRUCTURE",
            "pivot_score":          pivot_score,
            "confidence":           "LOW",
            "rationale":            "Pivot blocked — roll would produce a debit.",
            "allowed":              False,
        }

    # Gate: put diagonal only in negative gamma
    if pivot_score <= SENTIMENT_BEARISH_THRESHOLD:
        if "positive" in gamma:
            return {
                "pivot_recommendation": "HOLD_STRUCTURE",
                "pivot_score":          pivot_score,
                "confidence":           "LOW",
                "rationale":            "Bearish sentiment but gamma is positive — hold time spread instead of pivoting to puts.",
                "allowed":              True,
            }
        rec = "PIVOT_TO_DIAGONAL" if struct == "calendar" else "PIVOT_TO_PUTS"
        return {
            "pivot_recommendation": rec,
            "pivot_score":          pivot_score,
            "confidence":           "MEDIUM" if pivot_score < -0.50 else "LOW",
            "rationale":            f"Negative sentiment ({sentiment_score:.2f}) + {gamma} gamma + elevated put skew. Consider {rec.replace('_',' ').lower()}.",
            "allowed":              True,
        }

    # Gate: call calendar only when sentiment bullish AND put skew collapsed
    if pivot_score >= SENTIMENT_BULLISH_THRESHOLD:
        skew_collapsed = skew_num <= 0.01   # put skew near zero
        if skew_collapsed and "call" not in opt_side:
            return {
                "pivot_recommendation": "PIVOT_TO_CALLS",
                "pivot_score":          pivot_score,
                "confidence":           "HIGH" if pivot_score >= 0.60 else "MEDIUM",
                "rationale":            f"Bullish sentiment ({sentiment_score:.2f}) with collapsed put skew ({skew_num:.3f}). Pivot to call calendar.",
                "allowed":              True,
            }
        return {
            "pivot_recommendation": "PIVOT_TO_CALLS",
            "pivot_score":          pivot_score,
            "confidence":           "LOW",
            "rationale":            f"Bullish lean ({sentiment_score:.2f}) but put skew still elevated ({skew_num:.3f}). Call pivot possible but not ideal yet.",
            "allowed":              True,
        }

    # Neutral zone — hold current structure
    return {
        "pivot_recommendation": "HOLD_STRUCTURE",
        "pivot_score":          pivot_score,
        "confidence":           "HIGH",
        "rationale":            f"Sentiment score {sentiment_score:.2f} is within neutral band. No flip warranted.",
        "allowed":              True,
    }
