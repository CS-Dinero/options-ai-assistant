"""campaigns/campaign_transition_engine.py — Normalized transition candidates for the DEEP_ITM_CAMPAIGN family."""
from __future__ import annotations
from typing import Any

TRANSITION_FAMILIES = [
    "ROLL_SAME_SIDE","DEFENSIVE_ROLL","FLIP_SELECTIVELY",
    "COLLAPSE_TO_SPREAD","BANK_AND_REDUCE","DEFER_AND_WAIT",
]

def normalize_transition_candidate(family: str, quality_score: float, credit_est: float,
                                    reason: str, metadata: dict|None=None) -> dict[str,Any]:
    return {"transition_family":family,"transition_quality_score":round(quality_score,2),
            "transition_credit_est":round(credit_est,4),"transition_reason":reason,
            "metadata":metadata or {}}

def build_transition_candidates(roll_output: dict|None=None, defense_output: dict|None=None,
                                 flip_output: dict|None=None, collapse_output: dict|None=None,
                                 bank_reduce_signal: bool=False,
                                 campaign_recovered_pct: float=0.0) -> list[dict[str,Any]]:
    candidates=[]
    if roll_output and roll_output.get("approved"):
        candidates.append(normalize_transition_candidate("ROLL_SAME_SIDE",
            float(roll_output.get("future_roll_score",0)),
            float(roll_output.get("roll_credit_est",0)),
            roll_output.get("reason","Same-side roll candidate.")))
    if defense_output and defense_output.get("defense_candidate"):
        candidates.append(normalize_transition_candidate("DEFENSIVE_ROLL",
            float(defense_output.get("repair_survivability_score",0)),
            -float(defense_output.get("repair_cost_est",0)),
            defense_output.get("reason","Defensive repair candidate.")))
    if flip_output and flip_output.get("flip_candidate"):
        candidates.append(normalize_transition_candidate("FLIP_SELECTIVELY",
            float(flip_output.get("flip_quality_score",0)),
            float(flip_output.get("flip_credit_est",0)),
            flip_output.get("reason","Opposite-side flip candidate.")))
    if collapse_output and collapse_output.get("collapse_candidate"):
        candidates.append(normalize_transition_candidate("COLLAPSE_TO_SPREAD",
            float(collapse_output.get("collapse_quality_score",0)),
            float(collapse_output.get("projected_capital_relief",0)),
            collapse_output.get("reason","Collapse-to-spread candidate.")))
    if bank_reduce_signal or campaign_recovered_pct>=85.0:
        candidates.append(normalize_transition_candidate("BANK_AND_REDUCE",
            min(100.0,campaign_recovered_pct),-0.0,
            "Basis largely recovered; reduce or bank."))
    candidates.append(normalize_transition_candidate("DEFER_AND_WAIT",30.0,0.0,
                                                      "Wait for better execution conditions."))
    return sorted(candidates,key=lambda x: x["transition_quality_score"],reverse=True)
