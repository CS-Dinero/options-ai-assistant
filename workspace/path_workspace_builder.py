"""workspace/path_workspace_builder.py — Campaign-native operator workspace builder."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from campaigns.campaign_basis_ledger import CampaignLedgerSnapshot
from campaigns.campaign_state_engine import CampaignStateDecision
from compare.campaign_path_ranker import RankedPath

@dataclass(slots=True)
class CampaignWorkspaceInput:
    environment: str; symbol: str; position_id: str|None; campaign_id: str
    campaign_family: str; entry_family: str; current_structure: str; current_side: str
    short_strike: float|None=None; long_strike: float|None=None
    short_expiry: str|None=None; long_expiry: str|None=None
    short_dte: int|None=None; long_dte: int|None=None
    current_profit_percent: float|None=None; execution_surface_score: float|None=None
    timing_score: float|None=None; regime_alignment_score: float|None=None
    linked_review_ids: list[str]=field(default_factory=list)
    knowledge_context_summaries: list[str]=field(default_factory=list)
    primary_rationale: str=""

@dataclass(slots=True)
class CampaignWorkspace:
    workspace_type: str; environment: str
    symbol: str; position_id: str|None; campaign_id: str; campaign_family: str; entry_family: str
    current_structure: str; current_side: str
    campaign_ledger: dict[str,Any]; campaign_state: dict[str,Any]
    selected_path: dict[str,Any]|None; alternative_path: dict[str,Any]|None
    ranked_paths: list[dict[str,Any]]
    campaign_economics: dict[str,Any]; roll_panel: dict[str,Any]
    transition_panel: dict[str,Any]; execution_panel: dict[str,Any]
    linked_review_ids: list[str]; knowledge_context_summaries: list[str]; primary_rationale: str

def _path_to_dict(p: RankedPath|None) -> dict[str,Any]|None:
    if p is None: return None
    return {"path_code":p.path_code,"path_total_score":round(p.path_total_score,6),
            "campaign_recovery_score":round(p.campaign_recovery_score,6),
            "future_roll_score":round(p.future_roll_score,6),
            "flip_quality_score":round(p.flip_quality_score,6),
            "collapse_quality_score":round(p.collapse_quality_score,6),
            "campaign_complexity_score":round(p.campaign_complexity_score,6),
            "execution_quality_score":round(p.execution_quality_score,6),
            "regime_alignment_score":round(p.regime_alignment_score,6),
            "urgency_score":round(p.urgency_score,6),
            "mandate_fit_score":round(p.mandate_fit_score,6),
            "simplicity_score":round(p.simplicity_score,6),
            "capital_efficiency_score":round(p.capital_efficiency_score,6),
            "review_pressure_score":round(p.review_pressure_score,6),
            "projected_credit":round(p.projected_credit,6),
            "projected_debit":round(p.projected_debit,6),
            "projected_basis_after_action":round(p.projected_basis_after_action,6),
            "approved":p.approved,"reason":p.reason,"tradeoff_note":p.tradeoff_note,"details":p.details}

def _economics_panel(ls: CampaignLedgerSnapshot) -> dict[str,Any]:
    return {"opening_debit":round(ls.opening_debit,6),"opening_credit":round(ls.opening_credit,6),
            "realized_credit_collected":round(ls.realized_credit_collected,6),
            "realized_close_cost":round(ls.realized_close_cost,6),
            "repair_debit_paid":round(ls.repair_debit_paid,6),
            "net_campaign_basis":round(ls.net_campaign_basis,6),
            "campaign_recovered_pct":round(ls.campaign_recovered_pct,6),
            "campaign_cycle_count":int(ls.campaign_cycle_count),
            "campaign_realized_pnl":round(ls.campaign_realized_pnl,6)}

def _roll_panel(p: RankedPath|None) -> dict[str,Any]:
    if p is None:
        return {"roll_credit_est":None,"future_roll_score":None,"strike_improvement_score":None,
                "expected_move_clearance":None,"liquidity_score":None}
    d=p.details or {}
    return {"roll_credit_est":round(p.projected_credit,6),"future_roll_score":round(p.future_roll_score,6),
            "strike_improvement_score":d.get("strike_improvement_score"),
            "expected_move_clearance":d.get("expected_move_clearance"),
            "liquidity_score":d.get("liquidity_score"),
            "proposed_short_strike":d.get("proposed_short_strike"),
            "proposed_short_expiry":d.get("proposed_short_expiry")}

def _transition_panel(ranked: list[RankedPath]) -> dict[str,Any]:
    choices=[{"path_code":p.path_code,"path_total_score":round(p.path_total_score,6),
              "approved":p.approved,"projected_credit":round(p.projected_credit,6),
              "projected_debit":round(p.projected_debit,6),
              "projected_basis_after_action":round(p.projected_basis_after_action,6),
              "future_roll_score":round(p.future_roll_score,6),
              "flip_quality_score":round(p.flip_quality_score,6),
              "collapse_quality_score":round(p.collapse_quality_score,6),
              "reason":p.reason,"tradeoff_note":p.tradeoff_note} for p in ranked[:5]]
    def _first(code): return next((c for c in choices if c["path_code"]==code),None)
    return {"transition_choices":choices,"flip_candidate":_first("FLIP_SELECTIVELY"),
            "collapse_candidate":_first("COLLAPSE_TO_SPREAD"),"bank_reduce_candidate":_first("BANK_AND_REDUCE")}

def _execution_panel(wi: CampaignWorkspaceInput, sd: CampaignStateDecision,
                      p: RankedPath|None) -> dict[str,Any]:
    eq=None
    if wi.execution_surface_score is not None and wi.timing_score is not None:
        eq=round((float(wi.execution_surface_score)+float(wi.timing_score))/2.0,6)
    return {"campaign_action":sd.campaign_action,"campaign_state":sd.campaign_state,
            "campaign_urgency":int(sd.campaign_urgency),"execution_quality_score":eq,
            "selected_path_code":p.path_code if p else None,
            "selected_path_approved":p.approved if p else None,
            "selected_path_reason":p.reason if p else None}

def build_campaign_path_execution_workspace(wi: CampaignWorkspaceInput,
                                             ls: CampaignLedgerSnapshot,
                                             sd: CampaignStateDecision,
                                             ranked_paths: list[RankedPath]) -> CampaignWorkspace:
    sel=ranked_paths[0] if ranked_paths else None
    alt=ranked_paths[1] if len(ranked_paths)>1 else None
    ledger_dict={"campaign_id":ls.campaign_id,"campaign_family":ls.campaign_family,
                 "entry_family":ls.entry_family,"opening_debit":round(ls.opening_debit,6),
                 "opening_credit":round(ls.opening_credit,6),
                 "realized_credit_collected":round(ls.realized_credit_collected,6),
                 "realized_close_cost":round(ls.realized_close_cost,6),
                 "repair_debit_paid":round(ls.repair_debit_paid,6),
                 "net_campaign_basis":round(ls.net_campaign_basis,6),
                 "campaign_recovered_pct":round(ls.campaign_recovered_pct,6),
                 "campaign_cycle_count":int(ls.campaign_cycle_count),
                 "campaign_realized_pnl":round(ls.campaign_realized_pnl,6),
                 "current_structure":ls.current_structure,"current_side":ls.current_side}
    state_dict={"campaign_state":sd.campaign_state,"campaign_action":sd.campaign_action,
                "campaign_urgency":int(sd.campaign_urgency),"campaign_reason":sd.campaign_reason,
                "state_score":round(sd.state_score,6)}
    return CampaignWorkspace(
        workspace_type="PATH_EXECUTION_WORKSPACE",environment=wi.environment,
        symbol=wi.symbol,position_id=wi.position_id,campaign_id=wi.campaign_id,
        campaign_family=wi.campaign_family,entry_family=wi.entry_family,
        current_structure=wi.current_structure,current_side=wi.current_side,
        campaign_ledger=ledger_dict,campaign_state=state_dict,
        selected_path=_path_to_dict(sel),alternative_path=_path_to_dict(alt),
        ranked_paths=[_path_to_dict(p) for p in ranked_paths if p is not None],
        campaign_economics=_economics_panel(ls),roll_panel=_roll_panel(sel),
        transition_panel=_transition_panel(ranked_paths),
        execution_panel=_execution_panel(wi,sd,sel),
        linked_review_ids=list(wi.linked_review_ids),
        knowledge_context_summaries=list(wi.knowledge_context_summaries),
        primary_rationale=wi.primary_rationale or sd.campaign_reason)
