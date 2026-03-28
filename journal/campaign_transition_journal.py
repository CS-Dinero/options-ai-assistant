"""journal/campaign_transition_journal.py — Durable campaign journal rows bridging live→research→twin."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Literal
from datetime import datetime
from campaigns.campaign_basis_ledger import CampaignLedgerSnapshot
from lifecycle.campaign_lifecycle_classifier import CampaignLifecycleDecision
from compare.campaign_path_ranker import RankedPath

JournalStatus = Literal["OPEN","APPROVED","EXECUTED","DEFERRED","CANCELLED","CLOSED"]

@dataclass(slots=True)
class TransitionJournalRow:
    journal_id: str; timestamp_utc: str; environment: str
    symbol: str; position_id: str|None; campaign_id: str; campaign_family: str; entry_family: str
    current_structure: str|None; current_side: str|None
    campaign_state: str|None; campaign_action: str|None; campaign_urgency: int|None; campaign_reason: str|None
    path_recommended: str|None; path_selected: str|None; path_executed: str|None
    selected_transition_type: str|None; selected_transition_approved: bool|None; selected_transition_reason: str|None
    best_path_code: str|None; best_path_score: float|None; alt_path_code: str|None
    alt_path_score: float|None; path_score_gap: float|None
    net_campaign_basis: float|None; campaign_recovered_pct: float|None
    campaign_cycle_count: int|None; campaign_realized_pnl: float|None
    projected_credit: float|None; projected_debit: float|None; projected_basis_after_action: float|None
    future_roll_score: float|None; flip_quality_score: float|None; collapse_quality_score: float|None
    deployment_label: str|None; risk_envelope: str|None; maturity_level: str|None
    journal_status: JournalStatus; rationale: str
    notes: list[str]=field(default_factory=list); metadata: dict[str,Any]=field(default_factory=dict)

def _utcnow(): return datetime.utcnow().isoformat()
def _ro(v): return round(float(v),6) if v is not None else None
def _io(v): return int(v) if v is not None else None

def build_transition_journal_row(journal_id: str, environment: str, symbol: str, position_id: str|None,
                                  campaign_id: str, campaign_family: str, entry_family: str,
                                  current_structure: str|None, current_side: str|None,
                                  ledger_snapshot: CampaignLedgerSnapshot,
                                  lifecycle_decision: CampaignLifecycleDecision,
                                  ranked_paths: list[RankedPath]|None=None,
                                  path_selected: str|None=None, path_executed: str|None=None,
                                  deployment_label: str|None=None, risk_envelope: str|None=None,
                                  maturity_level: str|None=None, rationale: str="",
                                  notes: list[str]|None=None, metadata: dict[str,Any]|None=None,
                                  journal_status: JournalStatus="OPEN",
                                  timestamp_utc: str|None=None) -> TransitionJournalRow:
    rp=ranked_paths or []
    best=rp[0] if rp else None; alt=rp[1] if len(rp)>1 else None
    gap=round(best.path_total_score-alt.path_total_score,6) if best and alt else None
    pc=_ro(best.projected_credit) if best else None
    pd=_ro(best.projected_debit) if best else None
    pba=_ro(best.projected_basis_after_action) if best else None
    frs=_ro(best.future_roll_score) if best else None
    fqs=_ro(best.flip_quality_score) if best else None
    cqs=_ro(best.collapse_quality_score) if best else None
    return TransitionJournalRow(
        journal_id=journal_id,timestamp_utc=timestamp_utc or _utcnow(),environment=environment,
        symbol=symbol,position_id=position_id,campaign_id=campaign_id,campaign_family=campaign_family,
        entry_family=entry_family,current_structure=current_structure,current_side=current_side,
        campaign_state=lifecycle_decision.campaign_state,campaign_action=lifecycle_decision.campaign_action,
        campaign_urgency=lifecycle_decision.campaign_urgency,campaign_reason=lifecycle_decision.campaign_reason,
        path_recommended=lifecycle_decision.selected_transition_type,
        path_selected=path_selected,path_executed=path_executed,
        selected_transition_type=lifecycle_decision.selected_transition_type,
        selected_transition_approved=lifecycle_decision.selected_transition_approved,
        selected_transition_reason=lifecycle_decision.selected_transition_reason,
        best_path_code=best.path_code if best else None,best_path_score=_ro(best.path_total_score) if best else None,
        alt_path_code=alt.path_code if alt else None,alt_path_score=_ro(alt.path_total_score) if alt else None,
        path_score_gap=gap,net_campaign_basis=_ro(ledger_snapshot.net_campaign_basis),
        campaign_recovered_pct=_ro(ledger_snapshot.campaign_recovered_pct),
        campaign_cycle_count=_io(ledger_snapshot.campaign_cycle_count),
        campaign_realized_pnl=_ro(ledger_snapshot.campaign_realized_pnl),
        projected_credit=pc,projected_debit=pd,projected_basis_after_action=pba,
        future_roll_score=frs,flip_quality_score=fqs,collapse_quality_score=cqs,
        deployment_label=deployment_label,risk_envelope=risk_envelope,maturity_level=maturity_level,
        journal_status=journal_status,rationale=rationale or lifecycle_decision.campaign_reason,
        notes=list(notes or []),metadata=dict(metadata or {}))

def update_transition_journal_status(row: TransitionJournalRow, journal_status: JournalStatus,
                                      path_selected: str|None=None, path_executed: str|None=None,
                                      notes_to_add: list[str]|None=None, metadata_update: dict[str,Any]|None=None,
                                      timestamp_utc: str|None=None) -> TransitionJournalRow:
    from dataclasses import replace
    return replace(row,journal_status=journal_status,
                   path_selected=path_selected if path_selected is not None else row.path_selected,
                   path_executed=path_executed if path_executed is not None else row.path_executed,
                   notes=[*row.notes,*(notes_to_add or [])],
                   metadata={**row.metadata,**(metadata_update or {})},
                   timestamp_utc=timestamp_utc or row.timestamp_utc)

def mark_transition_executed(row: TransitionJournalRow, path_executed: str,
                               execution_notes: list[str]|None=None,
                               metadata_update: dict[str,Any]|None=None) -> TransitionJournalRow:
    return update_transition_journal_status(row,"EXECUTED",path_executed=path_executed,
                                             notes_to_add=execution_notes,metadata_update=metadata_update)

def mark_transition_deferred(row: TransitionJournalRow, defer_reason: str,
                              metadata_update: dict[str,Any]|None=None) -> TransitionJournalRow:
    return update_transition_journal_status(row,"DEFERRED",notes_to_add=[defer_reason],metadata_update=metadata_update)

def mark_transition_closed(row: TransitionJournalRow, close_reason: str,
                            metadata_update: dict[str,Any]|None=None) -> TransitionJournalRow:
    return update_transition_journal_status(row,"CLOSED",notes_to_add=[close_reason],metadata_update=metadata_update)

def transition_journal_row_to_dict(row: TransitionJournalRow) -> dict[str,Any]:
    return {"journal_id":row.journal_id,"timestamp_utc":row.timestamp_utc,"environment":row.environment,
            "symbol":row.symbol,"position_id":row.position_id,"campaign_id":row.campaign_id,
            "campaign_family":row.campaign_family,"entry_family":row.entry_family,
            "current_structure":row.current_structure,"current_side":row.current_side,
            "campaign_state":row.campaign_state,"campaign_action":row.campaign_action,
            "campaign_urgency":row.campaign_urgency,"campaign_reason":row.campaign_reason,
            "path_recommended":row.path_recommended,"path_selected":row.path_selected,
            "path_executed":row.path_executed,"selected_transition_type":row.selected_transition_type,
            "selected_transition_approved":row.selected_transition_approved,
            "selected_transition_reason":row.selected_transition_reason,
            "best_path_code":row.best_path_code,"best_path_score":row.best_path_score,
            "alt_path_code":row.alt_path_code,"alt_path_score":row.alt_path_score,
            "path_score_gap":row.path_score_gap,"net_campaign_basis":row.net_campaign_basis,
            "campaign_recovered_pct":row.campaign_recovered_pct,"campaign_cycle_count":row.campaign_cycle_count,
            "campaign_realized_pnl":row.campaign_realized_pnl,"projected_credit":row.projected_credit,
            "projected_debit":row.projected_debit,"projected_basis_after_action":row.projected_basis_after_action,
            "future_roll_score":row.future_roll_score,"flip_quality_score":row.flip_quality_score,
            "collapse_quality_score":row.collapse_quality_score,"deployment_label":row.deployment_label,
            "risk_envelope":row.risk_envelope,"maturity_level":row.maturity_level,
            "journal_status":row.journal_status,"rationale":row.rationale,
            "notes":row.notes,"metadata":row.metadata}
