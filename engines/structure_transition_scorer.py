"""
engines/structure_transition_scorer.py
Composite scorer for transition candidates.

score_transition(current_position, candidate_structure, skew_metrics,
                 rollability, liquidity, rules) → scored dict with approved flag
"""
from __future__ import annotations

from typing import Any

from config.transition_config import SCORING_WEIGHTS, TRANSITION_RULES


def _sf(v: Any, d: float = 0.0) -> float:
    try:
        return float(v) if v not in (None, "", "—") else d
    except (TypeError, ValueError):
        return d


def _credit_score(net_credit: float, min_credit: float) -> float:
    if min_credit <= 0: return 100.0
    if net_credit <= 0: return 0.0
    return max(0.0, min(100.0, (net_credit / min_credit) * 100.0))


def _assignment_inv(assignment_risk_score: float) -> float:
    """Invert assignment risk into a score (lower risk = higher score)."""
    return max(0.0, min(100.0, 100.0 - assignment_risk_score))


def _is_approved(
    net_credit:          float,
    min_flip_credit:     float,
    future_roll_score:   float,
    structure_score:     float,
    assignment_risk:     float,
) -> bool:
    rules = TRANSITION_RULES
    return (
        net_credit       >= min_flip_credit and
        future_roll_score >= rules["min_future_roll_score"] and
        structure_score   >= rules["min_structure_score"] and
        assignment_risk   <= rules["max_assignment_risk_score"]
    )


def score_transition(
    current_position:    dict[str, Any],
    candidate_structure: dict[str, Any],
    skew_metrics:        dict[str, Any],
    rollability:         dict[str, Any],
    liquidity:           dict[str, Any],
    rules:               dict[str, Any],
) -> dict[str, Any]:
    """
    Score one candidate transition.  Returns the input dict enriched with:
      approved, composite_score, credit_score, skew_score,
      future_roll_score, structure_score, liquidity_score, assignment_score
    """
    symbol          = str(current_position.get("symbol","")).upper()
    min_flip_credit = _sf(rules.get("min_flip_credit", 1.0))

    net_credit       = _sf(candidate_structure.get("transition_net_credit"))
    structure_score  = _sf(candidate_structure.get("structure_score", 60.0))
    assignment_risk  = _sf(candidate_structure.get("assignment_risk_score", 50.0))
    skew_score       = _sf(skew_metrics.get("skew_score", 0.0))
    liq_score        = _sf(liquidity.get("liquidity_score", candidate_structure.get("liquidity_score", 70.0)))
    future_roll_score = _sf(rollability.get("future_roll_score", 0.0))

    scores = {
        "credit_score":      _credit_score(net_credit, min_flip_credit),
        "skew_score":        skew_score,
        "future_roll_score": future_roll_score,
        "structure_score":   structure_score,
        "liquidity_score":   liq_score,
        "assignment_score":  _assignment_inv(assignment_risk),
    }

    composite = round(
        sum(scores[k] * SCORING_WEIGHTS[k] for k in SCORING_WEIGHTS), 2)

    approved = _is_approved(
        net_credit=net_credit,
        min_flip_credit=min_flip_credit,
        future_roll_score=future_roll_score,
        structure_score=structure_score,
        assignment_risk=assignment_risk,
    )

    return {
        **candidate_structure,
        "approved":          approved,
        "composite_score":   composite,
        "credit_score":      scores["credit_score"],
        "skew_score":        scores["skew_score"],
        "future_roll_score": scores["future_roll_score"],
        "structure_score":   scores["structure_score"],
        "liquidity_score":   scores["liquidity_score"],
        "assignment_score":  scores["assignment_score"],
    }
