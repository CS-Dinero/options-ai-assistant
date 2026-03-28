"""execution/transition_ticket_builder.py — Campaign-aware execution ticket builder (draft only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Literal

TicketAuthority = Literal["AUTO_DRAFT","HUMAN_APPROVAL","HUMAN_EXECUTION"]

@dataclass(slots=True)
class CampaignTransitionTicketInput:
    environment: str; symbol: str; position_id: str|None; campaign_id: str
    campaign_family: str; entry_family: str; current_structure: str; current_side: str
    campaign_state: str; campaign_action: str; campaign_urgency: int; campaign_reason: str
    opening_debit: float; opening_credit: float; realized_credit_collected: float
    realized_close_cost: float; repair_debit_paid: float; net_campaign_basis: float
    campaign_recovered_pct: float; campaign_cycle_count: int; campaign_realized_pnl: float
    selected_path: dict[str,Any]|None; alternative_path: dict[str,Any]|None
    deployment_label: str|None=None; risk_envelope: str|None=None; maturity_level: str|None=None
    linked_review_ids: list[str]=field(default_factory=list)
    knowledge_context_summaries: list[str]=field(default_factory=list)
    primary_rationale: str=""

@dataclass(slots=True)
class CampaignTransitionTicket:
    ticket_type: str; authority: TicketAuthority; environment: str
    symbol: str; position_id: str|None; campaign_id: str; campaign_family: str; entry_family: str
    current_structure: str; current_side: str
    selected_path: str|None; selected_path_approved: bool|None
    projected_credit: float|None; projected_debit: float|None; projected_basis_after_action: float|None
    roll_credit_est: float|None; future_roll_score: float|None
    flip_quality_score: float|None; collapse_quality_score: float|None
    deployment_label: str|None; risk_envelope: str|None; maturity_level: str|None
    campaign_snapshot: dict[str,Any]; execution_plan: dict[str,Any]
    review_context: dict[str,Any]; rationale: str; warnings: list[str]; notes: list[str]

def _get_f(d,k):
    v=d.get(k) if d else None
    return round(float(v),6) if v is not None else None

def _campaign_snapshot(ti: CampaignTransitionTicketInput) -> dict[str,Any]:
    return {"opening_debit":round(ti.opening_debit,6),"opening_credit":round(ti.opening_credit,6),
            "realized_credit_collected":round(ti.realized_credit_collected,6),
            "realized_close_cost":round(ti.realized_close_cost,6),
            "repair_debit_paid":round(ti.repair_debit_paid,6),
            "net_campaign_basis":round(ti.net_campaign_basis,6),
            "campaign_recovered_pct":round(ti.campaign_recovered_pct,6),
            "campaign_cycle_count":int(ti.campaign_cycle_count),
            "campaign_realized_pnl":round(ti.campaign_realized_pnl,6)}

def _execution_plan(ti: CampaignTransitionTicketInput) -> dict[str,Any]:
    s=ti.selected_path or {}; d=s.get("details",{}) or {}
    return {"campaign_state":ti.campaign_state,"campaign_action":ti.campaign_action,
            "campaign_urgency":int(ti.campaign_urgency),
            "selected_path_code":s.get("path_code"),"selected_path_score":s.get("path_total_score"),
            "selected_path_approved":s.get("approved"),
            "projected_credit":s.get("projected_credit"),"projected_debit":s.get("projected_debit"),
            "projected_basis_after_action":s.get("projected_basis_after_action"),
            "future_roll_score":s.get("future_roll_score"),
            "flip_quality_score":s.get("flip_quality_score"),
            "collapse_quality_score":s.get("collapse_quality_score"),
            "proposed_short_strike":d.get("proposed_short_strike"),
            "proposed_short_expiry":d.get("proposed_short_expiry"),
            "strike_improvement_score":d.get("strike_improvement_score"),
            "expected_move_clearance":d.get("expected_move_clearance"),
            "liquidity_score":d.get("liquidity_score"),
            "repair_type":d.get("repair_type"),"target_structure":d.get("target_structure"),
            "flip_to_side":d.get("flip_to_side"),
            "projected_capital_relief":d.get("projected_capital_relief")}

def _review_context(ti: CampaignTransitionTicketInput) -> dict[str,Any]:
    return {"linked_review_ids":list(ti.linked_review_ids),
            "knowledge_context_summaries":list(ti.knowledge_context_summaries),
            "alternative_path":ti.alternative_path}

def determine_ticket_authority(environment: str, selected_path: dict[str,Any]|None) -> TicketAuthority:
    # All ticket drafting is AUTO_DRAFT — human action required for live execution
    return "AUTO_DRAFT"

def build_ticket_warnings(ti: CampaignTransitionTicketInput) -> list[str]:
    s=ti.selected_path or {}; code=s.get("path_code"); approved=s.get("approved")
    w=[]
    if not s: w.append("No selected path attached."); return w
    if approved is False: w.append("Selected path not approved; treat as advisory only.")
    if ti.environment.upper()=="LIVE": w.append("LIVE tickets are draft-only and require human action.")
    if code=="DEFENSIVE_ROLL": w.append("Defensive roll indicates pressure; review survivability before action.")
    if code=="FLIP_SELECTIVELY": w.append("Flip changes campaign side; confirm regime and skew support.")
    if code=="COLLAPSE_TO_SPREAD": w.append("Collapse reduces optionality; confirm simplification preferred to harvest.")
    if ti.campaign_recovered_pct>=85.0 and code=="ROLL_SAME_SIDE":
        w.append("Campaign highly recovered; verify continuation superior to banking gains.")
    if ti.deployment_label and str(ti.deployment_label).upper() in("TOKEN","REDUCED"):
        w.append(f"Deployment label is {ti.deployment_label}; size should remain constrained.")
    return w

def build_ticket_notes(ti: CampaignTransitionTicketInput) -> list[str]:
    s=ti.selected_path or {}; alt=ti.alternative_path or {}; notes=[]
    if ti.primary_rationale: notes.append(ti.primary_rationale)
    if s.get("reason"): notes.append(f"Selected path: {s['reason']}")
    if s.get("tradeoff_note"): notes.append(f"Tradeoff: {s['tradeoff_note']}")
    if alt.get("path_code"):
        notes.append(f"Alternative: {alt.get('path_code')} (score={alt.get('path_total_score')})")
    notes.append(f"Campaign basis={ti.net_campaign_basis:.2f}, recovered={ti.campaign_recovered_pct:.1f}%.")
    if ti.risk_envelope: notes.append(f"Risk envelope: {ti.risk_envelope}")
    if ti.maturity_level: notes.append(f"Maturity: {ti.maturity_level}")
    return notes

def build_campaign_transition_ticket(ti: CampaignTransitionTicketInput) -> CampaignTransitionTicket:
    s=ti.selected_path or {}
    return CampaignTransitionTicket(
        ticket_type="CAMPAIGN_TRANSITION_TICKET",
        authority=determine_ticket_authority(ti.environment,s),
        environment=ti.environment,symbol=ti.symbol,position_id=ti.position_id,
        campaign_id=ti.campaign_id,campaign_family=ti.campaign_family,entry_family=ti.entry_family,
        current_structure=ti.current_structure,current_side=ti.current_side,
        selected_path=s.get("path_code"),selected_path_approved=s.get("approved"),
        projected_credit=_get_f(s,"projected_credit"),projected_debit=_get_f(s,"projected_debit"),
        projected_basis_after_action=_get_f(s,"projected_basis_after_action"),
        roll_credit_est=_get_f(s,"projected_credit"),
        future_roll_score=_get_f(s,"future_roll_score"),
        flip_quality_score=_get_f(s,"flip_quality_score"),
        collapse_quality_score=_get_f(s,"collapse_quality_score"),
        deployment_label=ti.deployment_label,risk_envelope=ti.risk_envelope,maturity_level=ti.maturity_level,
        campaign_snapshot=_campaign_snapshot(ti),execution_plan=_execution_plan(ti),
        review_context=_review_context(ti),rationale=ti.primary_rationale or ti.campaign_reason,
        warnings=build_ticket_warnings(ti),notes=build_ticket_notes(ti))

def campaign_transition_ticket_to_dict(t: CampaignTransitionTicket) -> dict[str,Any]:
    return {"ticket_type":t.ticket_type,"authority":t.authority,"environment":t.environment,
            "symbol":t.symbol,"position_id":t.position_id,"campaign_id":t.campaign_id,
            "campaign_family":t.campaign_family,"entry_family":t.entry_family,
            "current_structure":t.current_structure,"current_side":t.current_side,
            "selected_path":t.selected_path,"selected_path_approved":t.selected_path_approved,
            "projected_credit":t.projected_credit,"projected_debit":t.projected_debit,
            "projected_basis_after_action":t.projected_basis_after_action,
            "roll_credit_est":t.roll_credit_est,"future_roll_score":t.future_roll_score,
            "flip_quality_score":t.flip_quality_score,"collapse_quality_score":t.collapse_quality_score,
            "deployment_label":t.deployment_label,"risk_envelope":t.risk_envelope,
            "maturity_level":t.maturity_level,"campaign_snapshot":t.campaign_snapshot,
            "execution_plan":t.execution_plan,"review_context":t.review_context,
            "rationale":t.rationale,"warnings":t.warnings,"notes":t.notes}
