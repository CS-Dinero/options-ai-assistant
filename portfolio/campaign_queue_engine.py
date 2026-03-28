"""portfolio/campaign_queue_engine.py — Campaign-aware queue engine for DEEP_ITM_CAMPAIGN family."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from campaigns.campaign_basis_ledger import CampaignLedgerSnapshot
from compare.campaign_path_ranker import RankedPath
from lifecycle.campaign_lifecycle_classifier import CampaignLifecycleDecision

@dataclass(slots=True)
class CampaignQueueContext:
    environment: str; symbol: str; position_id: str|None; campaign_id: str
    campaign_family: str; entry_family: str; current_structure: str; current_side: str
    short_strike: float|None=None; long_strike: float|None=None
    short_expiry: str|None=None; long_expiry: str|None=None
    short_dte: int|None=None; long_dte: int|None=None
    current_profit_percent: float|None=None; distance_to_strike: float|None=None
    expected_move: float|None=None; execution_surface_score: float|None=None
    timing_score: float|None=None; regime_alignment_score: float|None=None
    campaign_complexity_score: float|None=None; deployment_label: str|None=None
    risk_envelope: str|None=None; maturity_level: str|None=None

@dataclass(slots=True)
class TransitionQueueRow:
    environment: str; symbol: str; position_id: str|None; campaign_id: str
    campaign_family: str; entry_family: str; current_structure: str; current_side: str
    campaign_state: str; campaign_action: str; campaign_urgency: int; campaign_reason: str
    selected_transition_type: str|None; selected_transition_approved: bool|None; selected_transition_reason: str|None
    net_campaign_basis: float; campaign_recovered_pct: float; campaign_cycle_count: int; campaign_realized_pnl: float
    current_profit_percent: float|None; short_dte: int|None; long_dte: int|None
    distance_to_strike: float|None; expected_move: float|None
    best_path_code: str|None; best_path_score: float|None; alt_path_code: str|None
    alt_path_score: float|None; path_score_gap: float|None
    future_roll_score: float|None; flip_quality_score: float|None; collapse_quality_score: float|None
    campaign_complexity_score: float|None; execution_quality_score: float|None; regime_alignment_score: float|None
    projected_credit: float|None; projected_debit: float|None; projected_basis_after_action: float|None
    queue_priority_score: float; queue_priority_band: str
    deployment_label: str|None; risk_envelope: str|None; maturity_level: str|None
    notes: list[str]=field(default_factory=list)

def _eq(es,ts):
    if es is None or ts is None: return None
    return round((float(es)+float(ts))/2.0,6)

def _best_alt(rp: list[RankedPath]|None) -> tuple[RankedPath|None,RankedPath|None]:
    rp=rp or []; return (rp[0] if rp else None),(rp[1] if len(rp)>1 else None)

def _band(score: float) -> str:
    if score>=85: return "ACT_NOW"
    if score>=70: return "DECIDE_NOW"
    if score>=50: return "WATCH_CLOSELY"
    return "IMPROVE_LATER"

ACTION_BONUS: dict = {"CLOSE":20.0,"DEFEND":18.0,"ROLL":14.0,"HARVEST":12.0,
                       "FLIP":10.0,"COLLAPSE":8.0,"BANK_REDUCE":6.0,"HOLD":0.0}

def score_queue_row(ld: CampaignLifecycleDecision, ls: CampaignLedgerSnapshot,
                     best: RankedPath|None, ctx: CampaignQueueContext) -> float:
    eq=_eq(ctx.execution_surface_score,ctx.timing_score)
    score=(0.28*float(ld.campaign_urgency)
           +0.18*float(best.path_total_score if best else 0)
           +0.12*float(best.future_roll_score if best else 0)
           +0.08*float(best.flip_quality_score if best else 0)
           +0.08*float(best.collapse_quality_score if best else 0)
           +0.10*float(eq if eq is not None else 50.0)
           +0.08*max(0.0,100.0-min(100.0,ls.net_campaign_basis*50.0))
           +0.04*min(100.0,ls.campaign_recovered_pct)
           +0.04*ACTION_BONUS.get(ld.campaign_action,0.0))
    if ld.selected_transition_approved is False: score+=7.5
    if ctx.environment.upper()=="LIVE": score+=5.0
    return round(min(100.0,max(0.0,score)),6)

def build_transition_queue_row(ctx: CampaignQueueContext, ls: CampaignLedgerSnapshot,
                                ld: CampaignLifecycleDecision,
                                ranked_paths: list[RankedPath]|None=None) -> TransitionQueueRow:
    best,alt=_best_alt(ranked_paths)
    eq=_eq(ctx.execution_surface_score,ctx.timing_score)
    score=score_queue_row(ld,ls,best,ctx); band=_band(score)
    gap=round(best.path_total_score-alt.path_total_score,6) if best and alt else None
    notes=[f"Basis={ls.net_campaign_basis:.2f}, Recovered={ls.campaign_recovered_pct:.1f}%."]
    if best: notes.append(f"BestPath={best.path_code} (score={best.path_total_score:.1f}, approved={best.approved}).")
    if alt: notes.append(f"AltPath={alt.path_code} (score={alt.path_total_score:.1f}).")
    if ld.selected_transition_reason: notes.append(f"SelectedTransitionReason={ld.selected_transition_reason}")
    for k,v in [("Deployment",ctx.deployment_label),("Envelope",ctx.risk_envelope),("Maturity",ctx.maturity_level)]:
        if v: notes.append(f"{k}={v}")
    return TransitionQueueRow(
        environment=ctx.environment,symbol=ctx.symbol,position_id=ctx.position_id,
        campaign_id=ctx.campaign_id,campaign_family=ctx.campaign_family,entry_family=ctx.entry_family,
        current_structure=ctx.current_structure,current_side=ctx.current_side,
        campaign_state=ld.campaign_state,campaign_action=ld.campaign_action,
        campaign_urgency=ld.campaign_urgency,campaign_reason=ld.campaign_reason,
        selected_transition_type=ld.selected_transition_type,
        selected_transition_approved=ld.selected_transition_approved,
        selected_transition_reason=ld.selected_transition_reason,
        net_campaign_basis=round(ls.net_campaign_basis,6),
        campaign_recovered_pct=round(ls.campaign_recovered_pct,6),
        campaign_cycle_count=int(ls.campaign_cycle_count),
        campaign_realized_pnl=round(ls.campaign_realized_pnl,6),
        current_profit_percent=ctx.current_profit_percent,short_dte=ctx.short_dte,
        long_dte=ctx.long_dte,distance_to_strike=ctx.distance_to_strike,expected_move=ctx.expected_move,
        best_path_code=best.path_code if best else None,
        best_path_score=round(best.path_total_score,6) if best else None,
        alt_path_code=alt.path_code if alt else None,
        alt_path_score=round(alt.path_total_score,6) if alt else None,
        path_score_gap=gap,
        future_roll_score=round(best.future_roll_score,6) if best else None,
        flip_quality_score=round(best.flip_quality_score,6) if best else None,
        collapse_quality_score=round(best.collapse_quality_score,6) if best else None,
        campaign_complexity_score=round(ctx.campaign_complexity_score,6) if ctx.campaign_complexity_score is not None else None,
        execution_quality_score=eq,
        regime_alignment_score=round(ctx.regime_alignment_score,6) if ctx.regime_alignment_score is not None else None,
        projected_credit=round(best.projected_credit,6) if best else None,
        projected_debit=round(best.projected_debit,6) if best else None,
        projected_basis_after_action=round(best.projected_basis_after_action,6) if best else None,
        queue_priority_score=score,queue_priority_band=band,
        deployment_label=ctx.deployment_label,risk_envelope=ctx.risk_envelope,
        maturity_level=ctx.maturity_level,notes=notes)

def transition_queue_row_to_dict(r: TransitionQueueRow) -> dict[str,Any]:
    return {"environment":r.environment,"symbol":r.symbol,"position_id":r.position_id,
            "campaign_id":r.campaign_id,"campaign_family":r.campaign_family,"entry_family":r.entry_family,
            "current_structure":r.current_structure,"current_side":r.current_side,
            "campaign_state":r.campaign_state,"campaign_action":r.campaign_action,
            "campaign_urgency":r.campaign_urgency,"campaign_reason":r.campaign_reason,
            "selected_transition_type":r.selected_transition_type,
            "selected_transition_approved":r.selected_transition_approved,
            "selected_transition_reason":r.selected_transition_reason,
            "net_campaign_basis":r.net_campaign_basis,"campaign_recovered_pct":r.campaign_recovered_pct,
            "campaign_cycle_count":r.campaign_cycle_count,"campaign_realized_pnl":r.campaign_realized_pnl,
            "current_profit_percent":r.current_profit_percent,"short_dte":r.short_dte,
            "long_dte":r.long_dte,"distance_to_strike":r.distance_to_strike,"expected_move":r.expected_move,
            "best_path_code":r.best_path_code,"best_path_score":r.best_path_score,
            "alt_path_code":r.alt_path_code,"alt_path_score":r.alt_path_score,
            "path_score_gap":r.path_score_gap,"future_roll_score":r.future_roll_score,
            "flip_quality_score":r.flip_quality_score,"collapse_quality_score":r.collapse_quality_score,
            "campaign_complexity_score":r.campaign_complexity_score,
            "execution_quality_score":r.execution_quality_score,"regime_alignment_score":r.regime_alignment_score,
            "projected_credit":r.projected_credit,"projected_debit":r.projected_debit,
            "projected_basis_after_action":r.projected_basis_after_action,
            "queue_priority_score":r.queue_priority_score,"queue_priority_band":r.queue_priority_band,
            "deployment_label":r.deployment_label,"risk_envelope":r.risk_envelope,
            "maturity_level":r.maturity_level,"notes":r.notes}

def build_transition_queue_rows(queue_inputs: list[CampaignQueueContext],
                                 ledger_snapshots: dict[str,CampaignLedgerSnapshot],
                                 lifecycle_decisions: dict[str,CampaignLifecycleDecision],
                                 ranked_paths: dict[str,list[RankedPath]]) -> list[TransitionQueueRow]:
    rows=[]
    for ctx in queue_inputs:
        ls=ledger_snapshots.get(ctx.campaign_id); ld=lifecycle_decisions.get(ctx.campaign_id)
        if not ls or not ld: continue
        rows.append(build_transition_queue_row(ctx,ls,ld,ranked_paths.get(ctx.campaign_id,[])))
    rows.sort(key=lambda x:(x.queue_priority_score,x.campaign_urgency,x.best_path_score or 0.0),reverse=True)
    return rows
