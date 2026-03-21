"""
engines/flip_optimizer.py
Scored multi-factor flip engine.

choose_best_flip(position, market_ctx) evaluates three flip candidates
and returns the highest-scoring one above threshold, or HOLD_STRUCTURE.

Scoring model (total = 100):
  credit improvement   30
  skew improvement     20
  sentiment alignment  15
  gamma alignment      15
  theta yield          10
  fill quality         10

Flip types:
  PIVOT_TO_CALLS      — put → call calendar (bullish sentiment + collapsing put skew)
  PIVOT_TO_PUTS       — call → put diagonal (bearish sentiment + expanding put skew + negative gamma)
  PIVOT_TO_DIAGONAL   — calendar → diagonal (price drifted 0.35–1.0 EM from center)
  HOLD_STRUCTURE      — no flip is better than current

Hard rules (enforced before scoring):
  - Never pivot if roll is a debit
  - Put diagonals only when gamma is negative
  - Call calendars only when sentiment bullish AND put skew collapses
"""
from __future__ import annotations

from typing import Any

from config.vh_config import (
    SENTIMENT_BULLISH_THRESHOLD, SENTIMENT_BEARISH_THRESHOLD, MIN_ROLL_NET_CREDIT,
)

FLIP_QUALITY_MIN_SCORE = 20.0   # below this → HOLD_STRUCTURE


def _sf(v: Any, d: float = 0.0) -> float:
    try:
        return float(v) if v not in (None, "", "—") else d
    except (TypeError, ValueError):
        return d


# ─────────────────────────────────────────────
# COMPONENT SCORERS
# ─────────────────────────────────────────────

def _credit_score(roll_credit: float) -> float:
    """Max 30 pts. Linear up to $6 credit."""
    return min(roll_credit * 5.0, 30.0)


def _skew_score(skew_change: float) -> float:
    """Max 20 pts. Larger absolute shift = more edge."""
    return min(abs(skew_change) * 5.0, 20.0)


def _sentiment_score(sentiment: float, flip_type: str) -> float:
    """Max 15 pts. Alignment = sentiment direction matches flip direction."""
    if flip_type == "PIVOT_TO_CALLS" and sentiment >= SENTIMENT_BULLISH_THRESHOLD:
        return min(sentiment * 25.0, 15.0)
    if flip_type in ("PIVOT_TO_PUTS", "PIVOT_TO_DIAGONAL") and sentiment <= SENTIMENT_BEARISH_THRESHOLD:
        return min(abs(sentiment) * 25.0, 15.0)
    return 0.0


def _gamma_score(gamma_regime: str, flip_type: str) -> float:
    """Max 15 pts. Regime alignment with flip direction."""
    g = gamma_regime.lower()
    if flip_type == "PIVOT_TO_CALLS"    and "positive" in g: return 15.0
    if flip_type == "PIVOT_TO_PUTS"     and "negative" in g: return 15.0
    if flip_type == "PIVOT_TO_DIAGONAL" and "negative" in g: return 12.0
    if flip_type == "PIVOT_TO_DIAGONAL" and "positive" in g: return  6.0
    return 0.0


def _theta_score(short_theta: float, long_theta: float) -> float:
    """Max 10 pts. Net theta yield after roll."""
    net = abs(short_theta) - abs(long_theta)
    return min(max(net * 50.0, 0.0), 10.0)


def _fill_score(bid_ask_width_pct: float) -> float:
    """Max 10 pts. Tighter market = better fill quality."""
    if bid_ask_width_pct <= 0.05: return 10.0
    if bid_ask_width_pct <= 0.10: return  7.0
    if bid_ask_width_pct <= 0.15: return  4.0
    return 1.0


def _total_score(
    flip_type:         str,
    roll_credit:       float,
    skew_change:       float,
    sentiment:         float,
    gamma_regime:      str,
    short_theta:       float,
    long_theta:        float,
    bid_ask_width_pct: float,
) -> float:
    return round(
        _credit_score(roll_credit)
        + _skew_score(skew_change)
        + _sentiment_score(sentiment, flip_type)
        + _gamma_score(gamma_regime, flip_type)
        + _theta_score(short_theta, long_theta)
        + _fill_score(bid_ask_width_pct),
        2,
    )


# ─────────────────────────────────────────────
# CANDIDATE BUILDERS
# ─────────────────────────────────────────────

def _context(position: dict, market_ctx: dict) -> dict:
    """Merge and resolve all inputs with multi-name aliases."""
    p = {**position}
    # delta — support both naming conventions
    p.setdefault("short_leg_delta", p.get("short_delta", 0.0))
    # skew
    p.setdefault("skew_spread_now",   p.get("current_skew", 0.0))
    p.setdefault("skew_spread_entry", p.get("entry_skew",   0.0))
    # gamma trap distance
    gd = p.get("gamma_trap_distance") or p.get("gamma_trap_distance_pct")
    p.setdefault("gamma_trap_distance_pct", gd)
    return {**p, **(market_ctx or {})}


def build_put_to_call_flip(position: dict, market_ctx: dict) -> dict:
    ctx          = _context(position, market_ctx)
    sentiment    = _sf(ctx.get("sentiment_score"))
    skew_change  = _sf(ctx.get("skew_spread_now")) - _sf(ctx.get("skew_spread_entry"))
    gamma        = str(ctx.get("gamma_regime", "")).lower()
    roll_credit  = _sf(ctx.get("proposed_roll_credit"))

    # Hard gates
    valid = (
        sentiment    >= SENTIMENT_BULLISH_THRESHOLD
        and skew_change  <= -2.0          # put skew collapsing
        and "negative" not in gamma       # not in negative gamma
        and roll_credit  >= MIN_ROLL_NET_CREDIT
    )
    score = _total_score(
        "PIVOT_TO_CALLS", roll_credit, skew_change, sentiment, gamma,
        _sf(ctx.get("short_theta")), _sf(ctx.get("long_theta")),
        _sf(ctx.get("bid_ask_width_pct"), 0.10),
    ) if valid else 0.0

    return {
        "flip_type":        "PIVOT_TO_CALLS",
        "valid":            valid,
        "flip_roll_credit": roll_credit,
        "skew_change":      round(skew_change, 3),
        "target_structure": "call_calendar",
        "flip_quality_score": score,
        "rationale":        "Bullish sentiment with collapsing put skew favors call calendar.",
    }


def build_call_to_put_flip(position: dict, market_ctx: dict) -> dict:
    ctx         = _context(position, market_ctx)
    sentiment   = _sf(ctx.get("sentiment_score"))
    skew_change = _sf(ctx.get("skew_spread_now")) - _sf(ctx.get("skew_spread_entry"))
    gamma       = str(ctx.get("gamma_regime", "")).lower()
    roll_credit = _sf(ctx.get("proposed_roll_credit"))

    # Hard gates — put diagonal only when gamma is negative
    valid = (
        sentiment    <= SENTIMENT_BEARISH_THRESHOLD
        and skew_change  >= 2.0           # put skew expanding
        and "negative" in gamma
        and roll_credit  >= MIN_ROLL_NET_CREDIT
    )
    score = _total_score(
        "PIVOT_TO_PUTS", roll_credit, skew_change, sentiment, gamma,
        _sf(ctx.get("short_theta")), _sf(ctx.get("long_theta")),
        _sf(ctx.get("bid_ask_width_pct"), 0.10),
    ) if valid else 0.0

    return {
        "flip_type":        "PIVOT_TO_PUTS",
        "valid":            valid,
        "flip_roll_credit": roll_credit,
        "skew_change":      round(skew_change, 3),
        "target_structure": "put_diagonal",
        "flip_quality_score": score,
        "rationale":        "Bearish sentiment with expanding put skew and negative gamma favor put diagonal.",
    }


def build_calendar_to_diagonal_flip(position: dict, market_ctx: dict) -> dict:
    ctx         = _context(position, market_ctx)
    em          = _sf(ctx.get("expected_move"))
    spot        = _sf(ctx.get("spot_price") or ctx.get("live_spot") or ctx.get("spot"))
    strike      = _sf(ctx.get("long_strike"))
    drift       = abs(spot - strike) / em if em > 0 else 0.0
    roll_credit = _sf(ctx.get("proposed_roll_credit"))
    gamma       = str(ctx.get("gamma_regime", "")).lower()
    skew_change = _sf(ctx.get("skew_spread_now")) - _sf(ctx.get("skew_spread_entry"))

    valid = 0.35 <= drift <= 1.0 and roll_credit >= MIN_ROLL_NET_CREDIT

    score = _total_score(
        "PIVOT_TO_DIAGONAL", roll_credit, skew_change,
        _sf(ctx.get("sentiment_score")), gamma,
        _sf(ctx.get("short_theta")), _sf(ctx.get("long_theta")),
        _sf(ctx.get("bid_ask_width_pct"), 0.10),
    ) if valid else 0.0

    return {
        "flip_type":        "PIVOT_TO_DIAGONAL",
        "valid":            valid,
        "flip_roll_credit": roll_credit,
        "skew_change":      round(skew_change, 3),
        "em_drift":         round(drift, 3),
        "target_structure": "diagonal",
        "flip_quality_score": score,
        "rationale":        f"Price drifted {drift:.1%} of EM; directional diagonal is more efficient.",
    }


# ─────────────────────────────────────────────
# MASTER CHOOSER
# ─────────────────────────────────────────────

def choose_best_flip(position: dict, market_ctx: dict) -> dict:
    """
    Evaluate all three flip candidates. Return the highest-scoring valid one
    above FLIP_QUALITY_MIN_SCORE, or HOLD_STRUCTURE.

    Always returns a complete dict with:
      flip_candidate        bool
      recommendation        HOLD_STRUCTURE | PIVOT_TO_CALLS | PIVOT_TO_PUTS | PIVOT_TO_DIAGONAL
      flip_type             same as recommendation when flip_candidate is True
      flip_target_structure target structure label
      flip_roll_credit      estimated net credit for the flip
      flip_quality_score    0–100 composite
      skew_change           skew delta since entry
      rationale             plain-English reason
    """
    candidates = [
        build_put_to_call_flip(position, market_ctx),
        build_call_to_put_flip(position, market_ctx),
        build_calendar_to_diagonal_flip(position, market_ctx),
    ]

    valid     = [c for c in candidates if c["valid"]]
    best      = max(valid, key=lambda c: c["flip_quality_score"], default=None)

    if not best or best["flip_quality_score"] < FLIP_QUALITY_MIN_SCORE:
        return {
            "flip_candidate":       False,
            "recommendation":       "HOLD_STRUCTURE",
            "flip_type":            "",
            "flip_target_structure":"",
            "flip_roll_credit":     0.0,
            "flip_quality_score":   0.0,
            "skew_change":          candidates[0]["skew_change"] if candidates else 0.0,
            "rationale":            "No flip candidate scores above threshold. Hold current structure.",
        }

    return {
        "flip_candidate":        True,
        "recommendation":        best["flip_type"],
        "flip_type":             best["flip_type"],
        "flip_target_structure": best.get("target_structure", ""),
        "flip_roll_credit":      best["flip_roll_credit"],
        "flip_quality_score":    best["flip_quality_score"],
        "skew_change":           best["skew_change"],
        "rationale":             best["rationale"],
        "all_candidates":        candidates,  # full detail for dashboard expander
    }
