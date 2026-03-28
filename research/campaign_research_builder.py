"""research/campaign_research_builder.py — Campaign-aware research dataset builder."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from campaigns.campaign_basis_ledger import CampaignLedgerSnapshot
from lifecycle.campaign_lifecycle_classifier import CampaignLifecycleDecision
from performance.trade_logger import CampaignTradeEvent, CampaignTradeRecord
from portfolio.campaign_queue_engine import TransitionQueueRow

@dataclass(slots=True)
class ResearchDatasetRow:
    environment: str; symbol: str; campaign_id: str; campaign_family: str
    entry_family: str; transition_family: str|None; current_structure: str|None; current_side: str|None
    campaign_state: str|None; campaign_action: str|None; campaign_urgency: int|None
    net_campaign_basis: float|None; campaign_recovered_pct: float|None
    campaign_cycle_count: int|None; campaign_realized_pnl: float|None; campaign_unrealized_pnl: float|None
    current_profit_percent: float|None; future_roll_score: float|None; flip_quality_score: float|None
    collapse_quality_score: float|None; campaign_complexity_score: float|None
    path_recommended: str|None; path_selected: str|None; path_executed: str|None
    selected_transition_type: str|None; selected_transition_approved: bool|None
    best_path_code: str|None; best_path_score: float|None; alt_path_code: str|None
    alt_path_score: float|None; path_score_gap: float|None
    projected_credit: float|None; projected_debit: float|None; projected_basis_after_action: float|None
    regime_at_decision: str|None; deployment_label: str|None; risk_envelope: str|None; maturity_level: str|None
    queue_priority_score: float|None; queue_priority_band: str|None
    timestamp_utc: str|None; row_source: str; metadata: dict[str,Any]

def _ro(v):
    if v is None: return None
    return round(float(v),6)
def _io(v):
    if v is None: return None
    return int(v)

def build_research_row_from_queue_row(row: TransitionQueueRow) -> ResearchDatasetRow:
    return ResearchDatasetRow(environment=row.environment,symbol=row.symbol,campaign_id=row.campaign_id,
        campaign_family=row.campaign_family,entry_family=row.entry_family,
        transition_family=row.selected_transition_type,current_structure=row.current_structure,
        current_side=row.current_side,campaign_state=row.campaign_state,campaign_action=row.campaign_action,
        campaign_urgency=row.campaign_urgency,net_campaign_basis=_ro(row.net_campaign_basis),
        campaign_recovered_pct=_ro(row.campaign_recovered_pct),campaign_cycle_count=_io(row.campaign_cycle_count),
        campaign_realized_pnl=_ro(row.campaign_realized_pnl),campaign_unrealized_pnl=None,
        current_profit_percent=_ro(row.current_profit_percent),future_roll_score=_ro(row.future_roll_score),
        flip_quality_score=_ro(row.flip_quality_score),collapse_quality_score=_ro(row.collapse_quality_score),
        campaign_complexity_score=_ro(row.campaign_complexity_score),
        path_recommended=row.best_path_code,path_selected=row.selected_transition_type,path_executed=None,
        selected_transition_type=row.selected_transition_type,
        selected_transition_approved=row.selected_transition_approved,
        best_path_code=row.best_path_code,best_path_score=_ro(row.best_path_score),
        alt_path_code=row.alt_path_code,alt_path_score=_ro(row.alt_path_score),
        path_score_gap=_ro(row.path_score_gap),projected_credit=_ro(row.projected_credit),
        projected_debit=_ro(row.projected_debit),
        projected_basis_after_action=_ro(row.projected_basis_after_action),
        regime_at_decision=None,deployment_label=row.deployment_label,
        risk_envelope=row.risk_envelope,maturity_level=row.maturity_level,
        queue_priority_score=_ro(row.queue_priority_score),queue_priority_band=row.queue_priority_band,
        timestamp_utc=None,row_source="QUEUE_ROW",
        metadata={"campaign_reason":row.campaign_reason,
                  "selected_transition_reason":row.selected_transition_reason,"notes":row.notes})

def build_research_row_from_trade_record(record: CampaignTradeRecord, environment: str) -> ResearchDatasetRow:
    return ResearchDatasetRow(environment=environment,symbol=record.symbol,campaign_id=record.campaign_id,
        campaign_family=record.campaign_family,entry_family=record.entry_family,
        transition_family=record.path_executed_last,current_structure=record.current_structure,
        current_side=record.current_side,campaign_state=None,campaign_action=None,campaign_urgency=None,
        net_campaign_basis=_ro(record.net_campaign_basis),campaign_recovered_pct=_ro(record.campaign_recovered_pct),
        campaign_cycle_count=_io(record.campaign_cycle_count),campaign_realized_pnl=_ro(record.campaign_realized_pnl),
        campaign_unrealized_pnl=_ro(record.campaign_unrealized_pnl),
        current_profit_percent=_ro(record.max_profit_percent_seen),
        future_roll_score=None,flip_quality_score=None,collapse_quality_score=None,campaign_complexity_score=None,
        path_recommended=record.path_recommended_last,path_selected=record.path_selected_last,
        path_executed=record.path_executed_last,selected_transition_type=record.path_selected_last,
        selected_transition_approved=None,best_path_code=None,best_path_score=None,
        alt_path_code=None,alt_path_score=None,path_score_gap=None,projected_credit=None,
        projected_debit=None,projected_basis_after_action=None,regime_at_decision=record.last_regime,
        deployment_label=record.deployment_label_last,risk_envelope=record.risk_envelope_last,
        maturity_level=record.maturity_level_last,queue_priority_score=None,queue_priority_band=None,
        timestamp_utc=record.closed_utc or record.opened_utc,row_source="TRADE_RECORD",
        metadata={"status":record.status,"opened_utc":record.opened_utc,"closed_utc":record.closed_utc,
                  "max_drawdown_percent_seen":record.max_drawdown_percent_seen,"event_count":len(record.events)})

def build_research_row_from_trade_event(event: CampaignTradeEvent, current_structure: str|None=None,
                                         current_side: str|None=None, environment: str="UNKNOWN") -> ResearchDatasetRow:
    return ResearchDatasetRow(environment=environment,symbol=event.symbol,campaign_id=event.campaign_id,
        campaign_family=event.campaign_family,entry_family=event.entry_family,
        transition_family=event.transition_family,current_structure=current_structure,current_side=current_side,
        campaign_state=None,campaign_action=None,campaign_urgency=None,
        net_campaign_basis=_ro(event.net_campaign_basis),campaign_recovered_pct=_ro(event.campaign_recovered_pct),
        campaign_cycle_count=_io(event.campaign_cycle_count),campaign_realized_pnl=_ro(event.net_cash_flow),
        campaign_unrealized_pnl=None,current_profit_percent=_ro(event.current_profit_percent),
        future_roll_score=_ro(event.future_roll_score_at_decision),
        flip_quality_score=_ro(event.flip_quality_score_at_decision),
        collapse_quality_score=_ro(event.collapse_quality_score_at_decision),campaign_complexity_score=None,
        path_recommended=event.path_recommended,path_selected=event.path_selected,path_executed=event.path_executed,
        selected_transition_type=event.transition_family,selected_transition_approved=None,
        best_path_code=None,best_path_score=None,alt_path_code=None,alt_path_score=None,path_score_gap=None,
        projected_credit=_ro(event.realized_credit),projected_debit=_ro(event.realized_debit),
        projected_basis_after_action=None,regime_at_decision=event.regime_at_decision,
        deployment_label=event.deployment_label,risk_envelope=event.risk_envelope,maturity_level=event.maturity_level,
        queue_priority_score=None,queue_priority_band=None,timestamp_utc=event.timestamp_utc,
        row_source="TRADE_EVENT",metadata={"event_type":event.event_type,"notes":event.notes,"metadata":event.metadata})

def build_research_row_from_lifecycle_decision(decision: CampaignLifecycleDecision,
                                                ledger_snapshot: CampaignLedgerSnapshot,
                                                symbol: str, environment: str,
                                                current_structure: str|None=None, current_side: str|None=None,
                                                deployment_label: str|None=None, risk_envelope: str|None=None,
                                                maturity_level: str|None=None) -> ResearchDatasetRow:
    ro=decision.roll_output or {}; fo=decision.flip_output or {}; co=decision.collapse_output or {}; do=decision.defense_output or {}
    proj_credit=_ro(ro.get("roll_credit_est") or fo.get("flip_credit_est") or co.get("projected_capital_relief"))
    proj_debit=_ro(do.get("repair_cost_est"))
    return ResearchDatasetRow(environment=environment,symbol=symbol,campaign_id=decision.campaign_id,
        campaign_family=decision.campaign_family,entry_family=decision.entry_family,
        transition_family=decision.selected_transition_type,current_structure=current_structure,
        current_side=current_side,campaign_state=decision.campaign_state,campaign_action=decision.campaign_action,
        campaign_urgency=decision.campaign_urgency,net_campaign_basis=_ro(ledger_snapshot.net_campaign_basis),
        campaign_recovered_pct=_ro(ledger_snapshot.campaign_recovered_pct),
        campaign_cycle_count=_io(ledger_snapshot.campaign_cycle_count),
        campaign_realized_pnl=_ro(ledger_snapshot.campaign_realized_pnl),campaign_unrealized_pnl=None,
        current_profit_percent=None,future_roll_score=_ro(ro.get("future_roll_score")),
        flip_quality_score=_ro(fo.get("flip_quality_score")),collapse_quality_score=_ro(co.get("collapse_quality_score")),
        campaign_complexity_score=None,path_recommended=decision.selected_transition_type,
        path_selected=decision.selected_transition_type,path_executed=None,
        selected_transition_type=decision.selected_transition_type,
        selected_transition_approved=decision.selected_transition_approved,
        best_path_code=None,best_path_score=None,alt_path_code=None,alt_path_score=None,path_score_gap=None,
        projected_credit=proj_credit,projected_debit=proj_debit,projected_basis_after_action=None,
        regime_at_decision=None,deployment_label=deployment_label,risk_envelope=risk_envelope,
        maturity_level=maturity_level,queue_priority_score=None,queue_priority_band=None,
        timestamp_utc=None,row_source="LIFECYCLE_DECISION",
        metadata={"campaign_reason":decision.campaign_reason,
                  "selected_transition_reason":decision.selected_transition_reason,"summary":decision.summary})

def build_research_rows_from_queue(rows: list[TransitionQueueRow]) -> list[ResearchDatasetRow]:
    return [build_research_row_from_queue_row(r) for r in rows]

def build_research_rows_from_trade_records(records: list[CampaignTradeRecord], environment: str) -> list[ResearchDatasetRow]:
    return [build_research_row_from_trade_record(r,environment) for r in records]

def build_research_rows_from_trade_events(events: list[CampaignTradeEvent], environment: str,
                                           current_structure_by_campaign_id: dict[str,str]|None=None,
                                           current_side_by_campaign_id: dict[str,str]|None=None) -> list[ResearchDatasetRow]:
    s=current_structure_by_campaign_id or {}; si=current_side_by_campaign_id or {}
    return [build_research_row_from_trade_event(e,s.get(e.campaign_id),si.get(e.campaign_id),environment) for e in events]

def research_dataset_row_to_dict(row: ResearchDatasetRow) -> dict[str,Any]:
    return {"environment":row.environment,"symbol":row.symbol,"campaign_id":row.campaign_id,
            "campaign_family":row.campaign_family,"entry_family":row.entry_family,
            "transition_family":row.transition_family,"current_structure":row.current_structure,
            "current_side":row.current_side,"campaign_state":row.campaign_state,
            "campaign_action":row.campaign_action,"campaign_urgency":row.campaign_urgency,
            "net_campaign_basis":row.net_campaign_basis,"campaign_recovered_pct":row.campaign_recovered_pct,
            "campaign_cycle_count":row.campaign_cycle_count,"campaign_realized_pnl":row.campaign_realized_pnl,
            "campaign_unrealized_pnl":row.campaign_unrealized_pnl,
            "current_profit_percent":row.current_profit_percent,"future_roll_score":row.future_roll_score,
            "flip_quality_score":row.flip_quality_score,"collapse_quality_score":row.collapse_quality_score,
            "campaign_complexity_score":row.campaign_complexity_score,
            "path_recommended":row.path_recommended,"path_selected":row.path_selected,
            "path_executed":row.path_executed,"selected_transition_type":row.selected_transition_type,
            "selected_transition_approved":row.selected_transition_approved,
            "best_path_code":row.best_path_code,"best_path_score":row.best_path_score,
            "alt_path_code":row.alt_path_code,"alt_path_score":row.alt_path_score,
            "path_score_gap":row.path_score_gap,"projected_credit":row.projected_credit,
            "projected_debit":row.projected_debit,"projected_basis_after_action":row.projected_basis_after_action,
            "regime_at_decision":row.regime_at_decision,"deployment_label":row.deployment_label,
            "risk_envelope":row.risk_envelope,"maturity_level":row.maturity_level,
            "queue_priority_score":row.queue_priority_score,"queue_priority_band":row.queue_priority_band,
            "timestamp_utc":row.timestamp_utc,"row_source":row.row_source,"metadata":row.metadata}
