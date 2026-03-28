"""lifecycle/flip_decision_engine.py — Evaluates opposite-side flips without over-flipping."""
from __future__ import annotations
from dataclasses import dataclass
from scanner.deep_itm_entry_filters import OptionLegQuote

@dataclass(slots=True)
class FlipDecisionInput:
    symbol: str; current_side: str; current_structure: str; current_profit_percent: float
    campaign_recovered_pct: float; net_campaign_basis: float
    regime_alignment_score: float; opposite_side_regime_alignment_score: float
    skew_support_score: float; execution_surface_score: float; timing_score: float
    campaign_complexity_score: float; same_side_roll_score: float
    projected_same_side_roll_credit: float; projected_flip_credit: float
    projected_flip_future_roll_score: float; projected_flip_recovery_ratio: float

@dataclass(slots=True)
class FlipDecisionResult:
    flip_candidate: bool; flip_to_side: str|None; flip_credit_est: float
    flip_quality_score: float; approved: bool; reason: str

@dataclass(slots=True)
class FlipDecisionConfig:
    min_flip_credit: float=0.25; min_flip_quality_score: float=65.0
    min_opposite_side_regime_alignment_score: float=60.0; min_skew_support_score: float=60.0
    min_projected_flip_future_roll_score: float=60.0; max_campaign_complexity_score: float=85.0

def score_flip_quality(fi: FlipDecisionInput) -> float:
    return round(0.20*min(100.0,max(0.0,fi.projected_flip_credit*100.0))
                 +0.20*min(100.0,max(0.0,fi.projected_flip_future_roll_score))
                 +0.15*min(100.0,max(0.0,fi.projected_flip_recovery_ratio*50.0))
                 +0.15*min(100.0,max(0.0,fi.opposite_side_regime_alignment_score))
                 +0.15*min(100.0,max(0.0,fi.skew_support_score))
                 +0.10*min(100.0,max(0.0,(fi.execution_surface_score+fi.timing_score)/2.0))
                 +0.05*max(0.0,100.0-min(100.0,fi.campaign_complexity_score)),6)

def evaluate_flip_candidate(flip_input: FlipDecisionInput,
                             cfg: FlipDecisionConfig|None=None) -> FlipDecisionResult:
    cfg=cfg or FlipDecisionConfig()
    flip_to="CALL" if flip_input.current_side.upper()=="PUT" else "PUT"
    fqs=score_flip_quality(flip_input)
    reasons=[]; approved=True
    if flip_input.projected_flip_credit<cfg.min_flip_credit:
        approved=False; reasons.append(f"Flip credit {flip_input.projected_flip_credit:.2f} below min {cfg.min_flip_credit:.2f}.")
    if fqs<cfg.min_flip_quality_score:
        approved=False; reasons.append(f"Flip quality {fqs:.1f} below min {cfg.min_flip_quality_score:.1f}.")
    if flip_input.opposite_side_regime_alignment_score<cfg.min_opposite_side_regime_alignment_score:
        approved=False; reasons.append("Opposite-side regime alignment insufficient.")
    if flip_input.skew_support_score<cfg.min_skew_support_score:
        approved=False; reasons.append("Skew support insufficient for flip.")
    if flip_input.projected_flip_future_roll_score<cfg.min_projected_flip_future_roll_score:
        approved=False; reasons.append("Projected future roll continuity weak after flip.")
    if flip_input.campaign_complexity_score>cfg.max_campaign_complexity_score:
        approved=False; reasons.append("Campaign complexity too high for flip.")
    if flip_input.same_side_roll_score>=fqs+10.0 and flip_input.projected_same_side_roll_credit>0.0:
        approved=False; reasons.append("Same-side continuation remains clearly superior.")
    reason="Approved opposite-side flip candidate." if not reasons else " | ".join(reasons)
    return FlipDecisionResult(flip_candidate=fqs>=cfg.min_flip_quality_score,flip_to_side=flip_to,
                               flip_credit_est=round(flip_input.projected_flip_credit,6),
                               flip_quality_score=fqs,approved=approved,reason=reason)
