"""campaigns/campaign_recovery_engine.py — Projects whether a campaign still has recovery potential."""
from __future__ import annotations
from typing import Any

def estimate_projected_recovery_ratio(projected_future_roll_credits: float, net_debit: float) -> float:
    return round(projected_future_roll_credits/max(0.01,net_debit),4)

def score_recovery_quality(projected_recovery_ratio: float, future_roll_score: float,
                            regime_alignment_score: float, execution_surface_score: float) -> float:
    ratio_score=min(100.0,max(0.0,(projected_recovery_ratio-1.0)*100.0))
    return round(0.40*ratio_score+0.30*min(100,future_roll_score)
                 +0.20*min(100,regime_alignment_score)+0.10*min(100,execution_surface_score),2)

def compute_campaign_recovery_context(ledger_snapshot: Any, projected_future_roll_credits: float,
                                       future_roll_score: float, regime_alignment_score: float,
                                       execution_surface_score: float) -> dict:
    basis=float(getattr(ledger_snapshot,"net_campaign_basis",0))
    ratio=estimate_projected_recovery_ratio(projected_future_roll_credits,max(0.01,basis))
    score=score_recovery_quality(ratio,future_roll_score,regime_alignment_score,execution_surface_score)
    reason=("Recovery potential strong." if score>=70 else
            "Recovery possible but uncertain." if score>=50 else
            "Recovery potential is weak — consider simplification or close.")
    return {"projected_recovery_ratio":ratio,"recovery_quality_score":score,"recovery_reason":reason}
