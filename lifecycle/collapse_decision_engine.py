"""lifecycle/collapse_decision_engine.py — Evaluates simplification into a spread."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(slots=True)
class CollapseDecisionInput:
    symbol: str; current_structure: str; current_side: str
    campaign_recovered_pct: float; net_campaign_basis: float; campaign_complexity_score: float
    current_profit_percent: float; long_leg_residual_value: float; projected_capital_relief: float
    execution_surface_score: float; timing_score: float; regime_alignment_score: float
    future_roll_score: float; same_side_roll_credit: float

@dataclass(slots=True)
class CollapseDecisionResult:
    collapse_candidate: bool; collapse_quality_score: float
    target_structure: str|None; projected_capital_relief: float; approved: bool; reason: str

@dataclass(slots=True)
class CollapseDecisionConfig:
    min_recovered_pct: float=60.0; min_collapse_quality_score: float=65.0
    min_projected_capital_relief: float=0.10; min_complexity_score: float=55.0
    max_future_roll_score_for_collapse_bias: float=75.0

def _target_structure_for_side(side: str) -> str:
    return "PUT_VERTICAL" if side.upper()=="PUT" else "CALL_VERTICAL"

def score_collapse_quality(ci: CollapseDecisionInput) -> float:
    roll_relief=max(0.0,100.0-min(100.0,ci.future_roll_score))
    return round(0.25*min(100.0,max(0.0,ci.campaign_recovered_pct))
                 +0.20*max(0.0,100.0-min(100.0,ci.net_campaign_basis*50.0))
                 +0.20*min(100.0,max(0.0,ci.campaign_complexity_score))
                 +0.15*min(100.0,max(0.0,ci.projected_capital_relief*100.0))
                 +0.10*min(100.0,max(0.0,(ci.execution_surface_score+ci.timing_score)/2.0))
                 +0.10*roll_relief,6)

def evaluate_collapse_candidate(collapse_input: CollapseDecisionInput,
                                 cfg: CollapseDecisionConfig|None=None) -> CollapseDecisionResult:
    cfg=cfg or CollapseDecisionConfig()
    target=_target_structure_for_side(collapse_input.current_side)
    cqs=score_collapse_quality(collapse_input)
    reasons=[]; approved=True
    if collapse_input.campaign_recovered_pct<cfg.min_recovered_pct:
        approved=False; reasons.append(f"Recovered {collapse_input.campaign_recovered_pct:.1f}% below min {cfg.min_recovered_pct:.1f}%.")
    if cqs<cfg.min_collapse_quality_score:
        approved=False; reasons.append(f"Collapse quality {cqs:.1f} below min {cfg.min_collapse_quality_score:.1f}.")
    if collapse_input.projected_capital_relief<cfg.min_projected_capital_relief:
        approved=False; reasons.append(f"Capital relief {collapse_input.projected_capital_relief:.2f} below min {cfg.min_projected_capital_relief:.2f}.")
    if collapse_input.campaign_complexity_score<cfg.min_complexity_score:
        approved=False; reasons.append("Complexity does not justify collapse.")
    if (collapse_input.future_roll_score>cfg.max_future_roll_score_for_collapse_bias
        and collapse_input.same_side_roll_credit>0.0):
        approved=False; reasons.append("Same-side continuation still attractive.")
    reason="Approved collapse-to-spread candidate." if not reasons else " | ".join(reasons)
    return CollapseDecisionResult(collapse_candidate=cqs>=cfg.min_collapse_quality_score,
                                   collapse_quality_score=cqs,target_structure=target,
                                   projected_capital_relief=round(collapse_input.projected_capital_relief,6),
                                   approved=approved,reason=reason)
