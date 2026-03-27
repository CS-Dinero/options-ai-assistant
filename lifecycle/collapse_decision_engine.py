"""lifecycle/collapse_decision_engine.py — Evaluates simplification into a spread."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(slots=True)
class CollapseResult:
    collapse_candidate: bool; collapse_quality_score: float
    target_structure: str; projected_capital_relief: float; reason: str

def score_collapse_quality(campaign_recovered_pct: float, remaining_basis: float,
                            long_value: float, campaign_complexity_score: float,
                            execution_surface_score: float) -> float:
    rec_score=min(100.0,campaign_recovered_pct)
    basis_score=max(0.0,100.0-max(0.0,remaining_basis)*20.0)
    comp_score=min(100.0,campaign_complexity_score)
    return round(0.35*rec_score+0.25*basis_score+0.25*comp_score+0.15*min(100,execution_surface_score),2)

def evaluate_collapse_candidate(campaign_recovered_pct: float, remaining_basis: float,
                                 long_value: float, campaign_complexity_score: float,
                                 execution_surface_score: float, capital_relief_est: float,
                                 min_recovery_pct: float=60.0,
                                 min_collapse_score: float=55.0) -> CollapseResult:
    cqs=score_collapse_quality(campaign_recovered_pct,remaining_basis,long_value,
                                campaign_complexity_score,execution_surface_score)
    reasons=[]
    if campaign_recovered_pct<min_recovery_pct:
        reasons.append(f"Recovery {campaign_recovered_pct:.1f}% below min {min_recovery_pct}%.")
    if cqs<min_collapse_score:
        reasons.append(f"Collapse quality {cqs:.1f} below min {min_collapse_score}.")
    ok=len(reasons)==0
    reason=("Collapse approved: basis recovered and simplification justified." if ok
            else "Collapse not justified: "+"; ".join(reasons))
    return CollapseResult(collapse_candidate=ok, collapse_quality_score=cqs,
                          target_structure="VERTICAL_SPREAD",
                          projected_capital_relief=round(capital_relief_est,4), reason=reason)
