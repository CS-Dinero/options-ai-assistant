"""
calculator/trade_scoring.py
Confidence scorer with missing-input normalization.

When a factor input is unavailable (e.g., gamma_regime = "unknown"),
its weight is redistributed proportionally across remaining factors.
This keeps scores honest and comparable across partial-data conditions.

Score range: 0–100
  80+  : strong trade
  65–79: tradable
  <65  : skip
"""

from typing import Optional
from config.settings import SCORE_WEIGHTS, SCORE_STRONG, SCORE_TRADABLE


# ─────────────────────────────────────────────
# FACTOR SCORERS — each returns float 0.0–1.0
# or None if input is unavailable
# ─────────────────────────────────────────────

def score_iv_regime(iv_regime: str, strategy_type: str) -> float:
    """
    Credit spreads thrive in rich IV (selling expensive premium).
    Debit spreads thrive in cheap IV (buying cheap premium).
    """
    credit_map  = {"cheap": 0.30, "moderate": 0.60, "elevated": 0.85, "rich": 1.00}
    debit_map   = {"cheap": 1.00, "moderate": 0.80, "elevated": 0.40, "rich": 0.20}
    neutral_map = {"cheap": 0.80, "moderate": 1.00, "elevated": 0.70, "rich": 0.40}

    if strategy_type in ("bear_call", "bull_put"):
        return credit_map.get(iv_regime, 0.5)
    elif strategy_type in ("bull_call_debit", "bear_put_debit"):
        return debit_map.get(iv_regime, 0.5)
    elif strategy_type in ("calendar", "diagonal"):
        return neutral_map.get(iv_regime, 0.5)   # calendars/diagonals prefer cheap-moderate
    return neutral_map.get(iv_regime, 0.5)


def score_gamma_regime(gamma_regime: str, strategy_type: str) -> Optional[float]:
    """
    Positive gamma (dealers long) → range-bound → good for credit spreads.
    Negative gamma (dealers short) → trending → good for debit spreads.
    Returns None when gamma_regime == "unknown" → triggers normalization.
    """
    if gamma_regime == "unknown":
        return None

    credit_map = {"positive": 1.00, "neutral": 0.60, "negative": 0.20}
    debit_map  = {"positive": 0.30, "neutral": 0.60, "negative": 1.00}

    if strategy_type in ("bear_call", "bull_put"):
        return credit_map.get(gamma_regime, 0.5)
    elif strategy_type in ("bull_call_debit", "bear_put_debit"):
        return debit_map.get(gamma_regime, 0.5)
    elif strategy_type == "calendar":
        return credit_map.get(gamma_regime, 0.6)  # calendar wants range-bound = positive gamma
    elif strategy_type == "diagonal":
        return debit_map.get(gamma_regime, 0.6)   # diagonal wants trending = negative gamma
    return 0.60


def score_em_placement(short_delta: float) -> float:
    """
    Better score when the short strike delta is further OTM.
    Lower delta = more cushion from the EM boundary.
    """
    abs_d = abs(short_delta)
    if abs_d <= 0.10:
        return 1.00
    elif abs_d <= 0.15:
        return 0.90
    elif abs_d <= 0.20:
        return 0.75
    elif abs_d <= 0.30:
        return 0.55
    return 0.30


def score_skew(skew_state: str, strategy_type: str) -> Optional[float]:
    """
    High put skew → selling puts is richly priced (bull put spreads benefit).
    Returns None when skew_state == "unknown" → triggers normalization.
    """
    if skew_state == "unknown":
        return None

    skew_maps = {
        "bull_put":        {"high_put_skew": 1.00, "normal_skew": 0.70, "flat_skew": 0.40},
        "bear_call":       {"high_put_skew": 0.60, "normal_skew": 0.70, "flat_skew": 0.90},
        "bull_call_debit": {"high_put_skew": 0.80, "normal_skew": 0.70, "flat_skew": 0.60},
        "bear_put_debit":  {"high_put_skew": 0.50, "normal_skew": 0.70, "flat_skew": 0.80},
    }
    return skew_maps.get(strategy_type, {}).get(skew_state, 0.60)


def score_term_structure(term_structure: str, strategy_type: str) -> float:
    """
    Contango (back > front IV) → front vol cheap relative to back
    → selling near-term credit is more efficient.
    Backwardation reverses this advantage.
    """
    credit_map = {"contango": 1.00, "flat": 0.65, "backwardation": 0.30}
    debit_map  = {"contango": 0.60, "flat": 0.75, "backwardation": 1.00}

    if strategy_type in ("bear_call", "bull_put"):
        return credit_map.get(term_structure, 0.50)
    elif strategy_type in ("bull_call_debit", "bear_put_debit"):
        return debit_map.get(term_structure, 0.50)
    elif strategy_type in ("calendar", "diagonal"):
        # calendars and diagonals strongly prefer contango (back > front IV)
        cal_diag_map = {"contango": 1.00, "flat": 0.70, "backwardation": 0.20}
        return cal_diag_map.get(term_structure, 0.50)
    return 0.65


def score_atr_regime(atr_trend: str, strategy_type: str) -> float:
    """
    Rising ATR = expanding realized vol → trend conditions → debit spreads better.
    Flat/falling ATR = contracting vol → range conditions → credit spreads better.
    """
    credit_map = {"flat": 1.00, "falling": 0.85, "rising": 0.45}
    debit_map  = {"rising": 1.00, "flat": 0.65, "falling": 0.45}

    if strategy_type in ("bear_call", "bull_put"):
        return credit_map.get(atr_trend, 0.50)
    elif strategy_type in ("bull_call_debit", "bear_put_debit"):
        return debit_map.get(atr_trend, 0.50)
    elif strategy_type in ("calendar", "diagonal"):
        # calendars prefer flat ATR; diagonals prefer moderate trend
        cal_diag_map = {"flat": 1.00, "falling": 0.80, "rising": 0.55}
        return cal_diag_map.get(atr_trend, 0.65)
    return 0.65


# ─────────────────────────────────────────────
# NORMALIZATION ENGINE
# ─────────────────────────────────────────────

def _normalize_weighted_score(raw_scores: dict[str, Optional[float]]) -> int:
    """
    Weighted sum with proportional redistribution of missing factor weights.

    If a factor returns None (unknown input), its weight is spread
    proportionally across the factors that do have values. This ensures
    the total score stays on a 0–100 scale regardless of missing data.

    Example: gamma (weight=20) unavailable → its 20 pts redistributed
    proportionally across the 5 remaining factors. A factor with weight=20
    absorbs 20 * (20/80) = 5 extra pts. A factor with weight=10 absorbs
    20 * (10/80) = 2.5 extra pts.
    """
    available  = {k: v for k, v in raw_scores.items() if v is not None}
    missing_wt = sum(SCORE_WEIGHTS[k] for k, v in raw_scores.items() if v is None)
    avail_wt   = sum(SCORE_WEIGHTS[k] for k in available)

    if avail_wt == 0:
        return 50   # all inputs missing — neutral score

    total = 0.0
    for factor, score_val in available.items():
        base_wt     = SCORE_WEIGHTS[factor]
        adjusted_wt = base_wt + missing_wt * (base_wt / avail_wt)
        total      += adjusted_wt * score_val

    return max(0, min(100, round(total)))


# ─────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────

def score_trade(candidate: dict, market: dict, derived: dict) -> int:
    """
    Compute confidence score for a trade candidate.

    Uses all six factors. Any factor returning None triggers proportional
    weight redistribution via _normalize_weighted_score.
    """
    strat = candidate["strategy_type"]

    raw_scores = {
        "iv_regime":    score_iv_regime(derived["iv_regime"], strat),
        "gamma_regime": score_gamma_regime(derived["gamma_regime"], strat),
        "em_placement": score_em_placement(candidate.get("short_delta", 0.15)),
        "skew":         score_skew(derived["skew_state"], strat),
        "term_struct":  score_term_structure(derived["term_structure"], strat),
        "atr_regime":   score_atr_regime(derived["atr_trend"], strat),
    }

    return _normalize_weighted_score(raw_scores)


def rank_candidates(candidates: list[dict]) -> list[dict]:
    """Sort candidates by confidence_score descending."""
    return sorted(candidates, key=lambda x: x["confidence_score"], reverse=True)


def get_score_breakdown(candidate: dict, derived: dict) -> dict:
    """
    Return the raw factor scores and weighted contributions for one candidate.
    Used by the printer and for debugging.
    """
    strat = candidate["strategy_type"]

    raw = {
        "IV Regime":      score_iv_regime(derived["iv_regime"], strat),
        "Gamma Regime":   score_gamma_regime(derived["gamma_regime"], strat),
        "EM Placement":   score_em_placement(candidate.get("short_delta", 0.15)),
        "Skew Fit":       score_skew(derived["skew_state"], strat),
        "Term Structure": score_term_structure(derived["term_structure"], strat),
        "ATR Regime":     score_atr_regime(derived["atr_trend"], strat),
    }

    weight_map = {
        "IV Regime":      SCORE_WEIGHTS["iv_regime"],
        "Gamma Regime":   SCORE_WEIGHTS["gamma_regime"],
        "EM Placement":   SCORE_WEIGHTS["em_placement"],
        "Skew Fit":       SCORE_WEIGHTS["skew"],
        "Term Structure": SCORE_WEIGHTS["term_struct"],
        "ATR Regime":     SCORE_WEIGHTS["atr_regime"],
    }

    available_wt = sum(weight_map[k] for k, v in raw.items() if v is not None)
    missing_wt   = sum(weight_map[k] for k, v in raw.items() if v is None)

    breakdown = {}
    for name, score_val in raw.items():
        base_wt = weight_map[name]
        if score_val is not None and available_wt > 0:
            adj_wt  = base_wt + missing_wt * (base_wt / available_wt)
            contrib = round(adj_wt * score_val, 1)
        else:
            adj_wt  = base_wt
            contrib = None

        breakdown[name] = {
            "raw":     score_val,
            "weight":  base_wt,
            "contrib": contrib,
        }

    return breakdown
