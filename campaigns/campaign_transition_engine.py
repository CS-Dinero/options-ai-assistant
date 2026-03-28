"""campaigns/campaign_transition_engine.py — Normalizes all transitions into one comparable schema."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal, Any
from lifecycle.net_credit_roll_engine import RollCandidate
from lifecycle.defensive_roll_engine import DefensiveRepairCandidate
from lifecycle.flip_decision_engine import FlipDecisionResult
from lifecycle.collapse_decision_engine import CollapseDecisionResult

TransitionType = Literal["ROLL_SAME_SIDE","DEFENSIVE_ROLL","FLIP_SELECTIVELY",
                          "COLLAPSE_TO_SPREAD","BANK_AND_REDUCE","DEFER_AND_WAIT"]

@dataclass(slots=True)
class CampaignTransitionContext:
    symbol: str; campaign_id: str; campaign_family: str; entry_family: str
    current_structure: str; current_side: str; net_campaign_basis: float
    campaign_recovered_pct: float; campaign_cycle_count: int; current_profit_percent: float
    future_roll_score: float; campaign_complexity_score: float
    execution_surface_score: float; timing_score: float; regime_alignment_score: float
    campaign_state: str; campaign_action: str; campaign_urgency: int; campaign_reason: str

@dataclass(slots=True)
class TransitionCandidate:
    transition_type: TransitionType; symbol: str; campaign_id: str
    campaign_family: str; entry_family: str; structure_before: str; structure_after: str|None
    side_before: str; side_after: str|None; projected_credit: float; projected_debit: float
    projected_basis_after_action: float; campaign_recovery_score: float; future_roll_score: float
    flip_quality_score: float; collapse_quality_score: float; campaign_complexity_score: float
    execution_quality_score: float; regime_alignment_score: float; urgency_score: float
    approved: bool; reason: str; details: dict[str,Any]

@dataclass(slots=True)
class TransitionEngineConfig:
    bank_reduce_recovered_pct: float=85.0; bank_reduce_basis_threshold: float=0.50
    defer_when_execution_below: float=55.0

def _c(v): return round(max(0.0,min(100.0,float(v))),6)
def _eq(es,ts): return _c((float(es)+float(ts))/2.0)
def _cr(rp,ba): return round(0.65*_c(rp)+0.35*max(0.0,100.0-min(100.0,ba*50.0)),6)
def _ba(basis,credit,debit): return round(max(0.0,float(basis)-float(credit)+float(debit)),6)

def _roll_cand(ctx,roll):
    pc=max(0.0,float(roll.roll_credit_est)); ba=_ba(ctx.net_campaign_basis,pc,0.0)
    return TransitionCandidate("ROLL_SAME_SIDE",ctx.symbol,ctx.campaign_id,ctx.campaign_family,
        ctx.entry_family,ctx.current_structure,ctx.current_structure,ctx.current_side,ctx.current_side,
        round(pc,6),round(max(0.0,-float(roll.roll_credit_est)),6),ba,_cr(ctx.campaign_recovered_pct,ba),
        _c(roll.future_roll_score),0.0,0.0,_c(ctx.campaign_complexity_score),
        _eq(ctx.execution_surface_score,ctx.timing_score),_c(ctx.regime_alignment_score),
        _c(ctx.campaign_urgency),bool(roll.approved),roll.reason,
        {"current_short_strike":roll.current_short_strike,"proposed_short_strike":roll.proposed_short_strike,
         "proposed_short_expiry":roll.proposed_short_expiry,"strike_improvement_score":roll.strike_improvement_score,
         "expected_move_clearance":roll.expected_move_clearance,"liquidity_score":roll.liquidity_score})

def _defense_cand(ctx,repair):
    pc=max(0.0,float(repair.new_credit)-float(repair.close_cost)); pd=max(0.0,float(repair.repair_cost_est))
    ba=_ba(ctx.net_campaign_basis,pc,pd)
    sa=ctx.current_structure if repair.repair_type!="CONVERT_TO_VERTICAL" else "VERTICAL"
    return TransitionCandidate("DEFENSIVE_ROLL",ctx.symbol,ctx.campaign_id,ctx.campaign_family,
        ctx.entry_family,ctx.current_structure,sa,ctx.current_side,ctx.current_side,
        round(pc,6),round(pd,6),ba,_cr(ctx.campaign_recovered_pct,ba),_c(repair.recovery_score),
        0.0,0.0,_c(ctx.campaign_complexity_score),_eq(ctx.execution_surface_score,ctx.timing_score),
        _c(ctx.regime_alignment_score),max(_c(ctx.campaign_urgency),85.0),
        bool(repair.approved),repair.reason,
        {"repair_type":repair.repair_type,"proposed_short_strike":repair.proposed_short_strike,
         "survivability_score":repair.survivability_score,"recovery_score":repair.recovery_score})

def _flip_cand(ctx,flip):
    pc=max(0.0,float(flip.flip_credit_est)); ba=_ba(ctx.net_campaign_basis,pc,0.0)
    return TransitionCandidate("FLIP_SELECTIVELY",ctx.symbol,ctx.campaign_id,ctx.campaign_family,
        ctx.entry_family,ctx.current_structure,ctx.current_structure,ctx.current_side,flip.flip_to_side,
        round(pc,6),0.0,ba,_cr(ctx.campaign_recovered_pct,ba),_c(ctx.future_roll_score),
        _c(flip.flip_quality_score),0.0,_c(ctx.campaign_complexity_score),
        _eq(ctx.execution_surface_score,ctx.timing_score),_c(ctx.regime_alignment_score),
        _c(ctx.campaign_urgency),bool(flip.approved),flip.reason,{"flip_to_side":flip.flip_to_side})

def _collapse_cand(ctx,col):
    pc=max(0.0,float(col.projected_capital_relief)); ba=_ba(ctx.net_campaign_basis,0.0,0.0)
    return TransitionCandidate("COLLAPSE_TO_SPREAD",ctx.symbol,ctx.campaign_id,ctx.campaign_family,
        ctx.entry_family,ctx.current_structure,col.target_structure,ctx.current_side,ctx.current_side,
        round(pc,6),0.0,ba,_cr(ctx.campaign_recovered_pct,ba),_c(ctx.future_roll_score),
        0.0,_c(col.collapse_quality_score),_c(ctx.campaign_complexity_score),
        _eq(ctx.execution_surface_score,ctx.timing_score),_c(ctx.regime_alignment_score),
        _c(ctx.campaign_urgency),bool(col.approved),col.reason,
        {"target_structure":col.target_structure,"projected_capital_relief":col.projected_capital_relief})

def _bank_cand(ctx):
    ba=max(0.0,round(ctx.net_campaign_basis,6))
    return TransitionCandidate("BANK_AND_REDUCE",ctx.symbol,ctx.campaign_id,ctx.campaign_family,
        ctx.entry_family,ctx.current_structure,None,ctx.current_side,None,0.0,0.0,ba,
        _cr(max(ctx.campaign_recovered_pct,90.0),ba),0.0,0.0,0.0,_c(ctx.campaign_complexity_score),
        _eq(ctx.execution_surface_score,ctx.timing_score),_c(ctx.regime_alignment_score),
        _c(ctx.campaign_urgency),True,"Campaign largely recovered; banking and reducing is justified.",{})

def _defer_cand(ctx):
    return TransitionCandidate("DEFER_AND_WAIT",ctx.symbol,ctx.campaign_id,ctx.campaign_family,
        ctx.entry_family,ctx.current_structure,ctx.current_structure,ctx.current_side,ctx.current_side,
        0.0,0.0,round(ctx.net_campaign_basis,6),_cr(ctx.campaign_recovered_pct,ctx.net_campaign_basis),
        _c(ctx.future_roll_score),0.0,0.0,_c(ctx.campaign_complexity_score),
        _eq(ctx.execution_surface_score,ctx.timing_score),_c(ctx.regime_alignment_score),
        _c(ctx.campaign_urgency),True,"No transition currently dominates; defer and monitor.",{})

def build_transition_candidates(ctx: CampaignTransitionContext,
                                 same_side_rolls: list[RollCandidate]|None=None,
                                 defensive_rolls: list[DefensiveRepairCandidate]|None=None,
                                 flip_result: FlipDecisionResult|None=None,
                                 collapse_result: CollapseDecisionResult|None=None,
                                 cfg: TransitionEngineConfig|None=None) -> list[TransitionCandidate]:
    cfg=cfg or TransitionEngineConfig(); out=[]
    approved_rolls=[r for r in (same_side_rolls or []) if r.approved]
    if approved_rolls: out.append(_roll_cand(ctx,approved_rolls[0]))
    approved_repairs=[r for r in (defensive_rolls or []) if r.approved]
    if approved_repairs: out.append(_defense_cand(ctx,approved_repairs[0]))
    if flip_result and flip_result.flip_candidate: out.append(_flip_cand(ctx,flip_result))
    if collapse_result and collapse_result.collapse_candidate: out.append(_collapse_cand(ctx,collapse_result))
    if ctx.campaign_recovered_pct>=cfg.bank_reduce_recovered_pct and ctx.net_campaign_basis<=cfg.bank_reduce_basis_threshold:
        out.append(_bank_cand(ctx))
    eq=_eq(ctx.execution_surface_score,ctx.timing_score)
    if not out or eq<cfg.defer_when_execution_below: out.append(_defer_cand(ctx))
    return out

def normalize_transition_candidate(candidate: TransitionCandidate) -> dict[str,Any]:
    return {"transition_type":candidate.transition_type,"symbol":candidate.symbol,
            "campaign_id":candidate.campaign_id,"campaign_family":candidate.campaign_family,
            "entry_family":candidate.entry_family,"structure_before":candidate.structure_before,
            "structure_after":candidate.structure_after,"side_before":candidate.side_before,
            "side_after":candidate.side_after,"projected_credit":round(candidate.projected_credit,6),
            "projected_debit":round(candidate.projected_debit,6),
            "projected_basis_after_action":round(candidate.projected_basis_after_action,6),
            "campaign_recovery_score":round(candidate.campaign_recovery_score,6),
            "future_roll_score":round(candidate.future_roll_score,6),
            "flip_quality_score":round(candidate.flip_quality_score,6),
            "collapse_quality_score":round(candidate.collapse_quality_score,6),
            "campaign_complexity_score":round(candidate.campaign_complexity_score,6),
            "execution_quality_score":round(candidate.execution_quality_score,6),
            "regime_alignment_score":round(candidate.regime_alignment_score,6),
            "urgency_score":round(candidate.urgency_score,6),
            "approved":candidate.approved,"reason":candidate.reason,"details":candidate.details}
