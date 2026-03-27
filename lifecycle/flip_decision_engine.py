"""lifecycle/flip_decision_engine.py — Evaluates opposite-side flips without over-flipping."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(slots=True)
class FlipResult:
    flip_candidate: bool; flip_to_side: str; flip_credit_est: float
    flip_quality_score: float; reason: str

def score_flip_quality(regime_alignment_score: float, skew_score: float,
                        future_roll_score: float, em_clearance: float,
                        campaign_recovered_pct: float) -> float:
    return round(0.25*min(100,regime_alignment_score)+0.25*min(100,skew_score)
                 +0.20*min(100,future_roll_score)+0.15*min(100,em_clearance*100)
                 +0.15*min(100,campaign_recovered_pct),2)

def evaluate_flip_candidate(current_side: str, proposed_flip_mid: float, close_cost: float,
                              regime_alignment_score: float, skew_score: float,
                              future_roll_score: float, em_clearance: float,
                              campaign_recovered_pct: float, campaign_complexity_score: float,
                              execution_surface_score: float,
                              min_flip_score: float=65.0) -> FlipResult:
    flip_to="CALL" if current_side.upper()=="PUT" else "PUT"
    credit_est=round(proposed_flip_mid-close_cost,4)
    fqs=score_flip_quality(regime_alignment_score,skew_score,future_roll_score,em_clearance,campaign_recovered_pct)
    reasons=[]
    if regime_alignment_score<60: reasons.append("Regime does not support direction change.")
    if credit_est<0.10:           reasons.append("Flip credit too low.")
    if campaign_complexity_score>80: reasons.append("Campaign already too complex for flip.")
    if execution_surface_score<55: reasons.append("Execution surface too weak for flip.")
    if fqs<min_flip_score:        reasons.append(f"Flip quality {fqs:.1f} below minimum {min_flip_score}.")
    ok=len(reasons)==0
    reason=("Flip approved: regime, credit, and quality all support transition." if ok
            else "Flip rejected: "+"; ".join(reasons))
    return FlipResult(ok,flip_to,credit_est,fqs,reason)
