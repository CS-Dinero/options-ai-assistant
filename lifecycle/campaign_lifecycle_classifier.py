"""lifecycle/campaign_lifecycle_classifier.py — Coordinates all campaign lifecycle engines."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from campaigns.campaign_basis_ledger import CampaignLedgerSnapshot
from campaigns.campaign_state_engine import (
    CampaignAction, CampaignState, CampaignStateDecision, CampaignStateInput, classify_campaign_state,
)
from lifecycle.net_credit_roll_engine import RollCandidate
from lifecycle.defensive_roll_engine import DefensiveRepairCandidate
from lifecycle.flip_decision_engine import FlipDecisionResult
from lifecycle.collapse_decision_engine import CollapseDecisionResult

@dataclass(slots=True)
class CampaignLifecycleClassifierConfig:
    harvest_min_pct: float=30.0; harvest_target_pct: float=40.0; high_risk_dte: int=3
    prefer_same_side_roll_margin: float=7.5; prefer_defensive_roll_margin: float=7.5
    prefer_flip_margin: float=5.0; prefer_collapse_margin: float=5.0
    min_roll_score_to_promote: float=65.0; min_flip_score_to_promote: float=70.0
    min_collapse_score_to_promote: float=70.0; min_defense_score_to_promote: float=60.0

@dataclass(slots=True)
class CampaignLifecycleContext:
    symbol: str; current_structure: str; current_side: str
    short_dte: int; long_dte: int; distance_to_strike: float; expected_move: float
    current_profit_percent: float; execution_surface_score: float; timing_score: float
    regime_alignment_score: float; campaign_complexity_score: float

@dataclass(slots=True)
class CampaignLifecycleDecision:
    campaign_id: str; campaign_family: str; entry_family: str
    campaign_state: CampaignState; campaign_action: CampaignAction
    campaign_urgency: int; campaign_reason: str; state_score: float
    selected_transition_type: str|None; selected_transition_approved: bool|None
    selected_transition_reason: str|None
    roll_output: dict[str,Any]|None; defense_output: dict[str,Any]|None
    flip_output: dict[str,Any]|None; collapse_output: dict[str,Any]|None
    summary: str

def _best_roll(candidates: list[RollCandidate]|None) -> RollCandidate|None:
    approved=[c for c in (candidates or []) if c.approved]
    if not approved: return None
    approved.sort(key=lambda x:(x.roll_credit_est,x.future_roll_score,x.strike_improvement_score,x.expected_move_clearance),reverse=True)
    return approved[0]

def _best_defense(candidates: list[DefensiveRepairCandidate]|None) -> DefensiveRepairCandidate|None:
    approved=[c for c in (candidates or []) if c.approved]
    if not approved: return None
    approved.sort(key=lambda x:(x.survivability_score,x.recovery_score,-max(0.0,x.repair_cost_est),x.time_extension_score),reverse=True)
    return approved[0]

def _state_input(ctx: CampaignLifecycleContext, ls: CampaignLedgerSnapshot,
                  br: RollCandidate|None, bd: DefensiveRepairCandidate|None,
                  flip: FlipDecisionResult|None, col: CollapseDecisionResult|None) -> CampaignStateInput:
    return CampaignStateInput(
        symbol=ctx.symbol,current_structure=ctx.current_structure,current_side=ctx.current_side,
        short_dte=ctx.short_dte,long_dte=ctx.long_dte,distance_to_strike=ctx.distance_to_strike,
        expected_move=ctx.expected_move,current_profit_percent=ctx.current_profit_percent,
        execution_surface_score=ctx.execution_surface_score,timing_score=ctx.timing_score,
        regime_alignment_score=ctx.regime_alignment_score,
        future_roll_score=br.future_roll_score if br else 0.0,
        flip_quality_score=flip.flip_quality_score if flip else 0.0,
        collapse_quality_score=col.collapse_quality_score if col else 0.0,
        campaign_complexity_score=ctx.campaign_complexity_score,
        net_campaign_basis=ls.net_campaign_basis,campaign_recovered_pct=ls.campaign_recovered_pct,
        roll_credit_est=br.roll_credit_est if br else 0.0,
        defensive_repair_score=bd.survivability_score if bd else 0.0)

def _roll_dict(c: RollCandidate|None) -> dict[str,Any]|None:
    if not c: return None
    return {"approved":c.approved,"reason":c.reason,"current_short_strike":c.current_short_strike,
            "current_short_expiry":c.current_short_expiry,"proposed_short_strike":c.proposed_short_strike,
            "proposed_short_expiry":c.proposed_short_expiry,"proposed_short_mid":c.proposed_short_mid,
            "close_cost":c.close_cost,"roll_credit_est":c.roll_credit_est,"future_roll_score":c.future_roll_score,
            "strike_improvement_score":c.strike_improvement_score,"expected_move_clearance":c.expected_move_clearance,
            "liquidity_score":c.liquidity_score}

def _defense_dict(c: DefensiveRepairCandidate|None) -> dict[str,Any]|None:
    if not c: return None
    return {"approved":c.approved,"reason":c.reason,"repair_type":c.repair_type,
            "current_short_strike":c.current_short_strike,"current_short_expiry":c.current_short_expiry,
            "proposed_short_strike":c.proposed_short_strike,"proposed_short_expiry":c.proposed_short_expiry,
            "close_cost":c.close_cost,"new_credit":c.new_credit,"repair_cost_est":c.repair_cost_est,
            "strike_relief_score":c.strike_relief_score,"time_extension_score":c.time_extension_score,
            "survivability_score":c.survivability_score,"recovery_score":c.recovery_score,
            "liquidity_score":c.liquidity_score,"expected_move_clearance":c.expected_move_clearance}

def _flip_dict(r: FlipDecisionResult|None) -> dict[str,Any]|None:
    if not r: return None
    return {"flip_candidate":r.flip_candidate,"approved":r.approved,"reason":r.reason,
            "flip_to_side":r.flip_to_side,"flip_credit_est":r.flip_credit_est,"flip_quality_score":r.flip_quality_score}

def _collapse_dict(r: CollapseDecisionResult|None) -> dict[str,Any]|None:
    if not r: return None
    return {"collapse_candidate":r.collapse_candidate,"approved":r.approved,"reason":r.reason,
            "collapse_quality_score":r.collapse_quality_score,"target_structure":r.target_structure,
            "projected_capital_relief":r.projected_capital_relief}

def _select_transition(sd: CampaignStateDecision, br: RollCandidate|None, bd: DefensiveRepairCandidate|None,
                        flip: FlipDecisionResult|None, col: CollapseDecisionResult|None,
                        cfg: CampaignLifecycleClassifierConfig) -> tuple[str|None,bool|None,str|None]:
    s=sd.campaign_state
    if s=="BROKEN": return ("CLOSE",True,"Campaign broken; close or hard repair required.")
    if s=="BANK_REDUCE": return ("BANK_AND_REDUCE",True,"Campaign largely recovered; bank and reduce.")
    if s=="COLLAPSE_CANDIDATE":
        if col and col.approved: return ("COLLAPSE_TO_SPREAD",True,col.reason)
        return ("COLLAPSE_TO_SPREAD",False,"Collapse candidate identified but not approved.")
    if s=="DEFENSIVE_ROLL":
        if bd and bd.approved and bd.survivability_score>=cfg.min_defense_score_to_promote:
            return ("DEFENSIVE_ROLL",True,bd.reason)
        return ("DEFENSIVE_ROLL",False,"Defensive roll state but no approved repair dominates.")
    if s=="ROLL_READY":
        if br and br.approved and br.future_roll_score>=cfg.min_roll_score_to_promote:
            return ("ROLL_SAME_SIDE",True,br.reason)
        return ("HARVEST",True,"Harvest ready but no approved continuation roll dominates.")
    if s=="HARVEST_READY":
        if br and br.approved and br.future_roll_score>=cfg.min_roll_score_to_promote:
            return ("ROLL_SAME_SIDE",True,br.reason)
        return ("HARVEST",True,"Harvest threshold reached; harvest without continuation.")
    if s=="FLIP_REVIEW":
        if flip and flip.approved and flip.flip_quality_score>=cfg.min_flip_score_to_promote:
            return ("FLIP_SELECTIVELY",True,flip.reason)
        if br and br.approved: return ("ROLL_SAME_SIDE",True,"Flip review active; same-side stronger.")
        return ("HOLD",False,"Flip review active but no approved flip dominates.")
    return ("HOLD",True,"Defer and monitor.")

def build_campaign_lifecycle_decision(campaign_id: str, campaign_family: str, entry_family: str,
                                       ctx: CampaignLifecycleContext, ls: CampaignLedgerSnapshot,
                                       same_side_rolls: list[RollCandidate]|None=None,
                                       defensive_rolls: list[DefensiveRepairCandidate]|None=None,
                                       flip_result: FlipDecisionResult|None=None,
                                       collapse_result: CollapseDecisionResult|None=None,
                                       cfg: CampaignLifecycleClassifierConfig|None=None) -> CampaignLifecycleDecision:
    cfg=cfg or CampaignLifecycleClassifierConfig()
    br=_best_roll(same_side_rolls); bd=_best_defense(defensive_rolls)
    si=_state_input(ctx,ls,br,bd,flip_result,collapse_result)
    sd=classify_campaign_state(si,cfg.harvest_min_pct,cfg.harvest_target_pct,cfg.high_risk_dte)
    tt,ta,tr=_select_transition(sd,br,bd,flip_result,collapse_result,cfg)
    summary=" | ".join(filter(None,[f"Campaign {campaign_id}",f"Entry={entry_family}",
                                     f"State={sd.campaign_state}",f"Action={sd.campaign_action}",
                                     f"SelectedTransition={tt}" if tt else None,
                                     f"Reason={tr}" if tr else None]))
    return CampaignLifecycleDecision(campaign_id=campaign_id,campaign_family=campaign_family,
        entry_family=entry_family,campaign_state=sd.campaign_state,campaign_action=sd.campaign_action,
        campaign_urgency=sd.campaign_urgency,campaign_reason=sd.campaign_reason,state_score=sd.state_score,
        selected_transition_type=tt,selected_transition_approved=ta,selected_transition_reason=tr,
        roll_output=_roll_dict(br),defense_output=_defense_dict(bd),
        flip_output=_flip_dict(flip_result),collapse_output=_collapse_dict(collapse_result),summary=summary)

def campaign_lifecycle_decision_to_dict(d: CampaignLifecycleDecision) -> dict[str,Any]:
    return {"campaign_id":d.campaign_id,"campaign_family":d.campaign_family,"entry_family":d.entry_family,
            "campaign_state":d.campaign_state,"campaign_action":d.campaign_action,
            "campaign_urgency":d.campaign_urgency,"campaign_reason":d.campaign_reason,
            "state_score":round(d.state_score,6),"selected_transition_type":d.selected_transition_type,
            "selected_transition_approved":d.selected_transition_approved,
            "selected_transition_reason":d.selected_transition_reason,
            "roll_output":d.roll_output,"defense_output":d.defense_output,
            "flip_output":d.flip_output,"collapse_output":d.collapse_output,"summary":d.summary}
