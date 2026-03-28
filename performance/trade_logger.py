"""performance/trade_logger.py — Campaign-level trade logger."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Literal
from datetime import datetime

CampaignEventType = Literal[
    "OPEN_ENTRY","HARVEST","ROLL_SAME_SIDE","DEFENSIVE_ROLL",
    "FLIP_SELECTIVELY","COLLAPSE_TO_SPREAD","BANK_AND_REDUCE","DEFER_AND_WAIT","CLOSE",
]
CampaignStatus = Literal["OPEN","ACTIVE","REDUCED","CLOSED"]

@dataclass(slots=True)
class CampaignTradeEvent:
    event_id: str; campaign_id: str; timestamp_utc: str; event_type: CampaignEventType
    symbol: str; campaign_family: str; entry_family: str; transition_family: str|None=None
    path_recommended: str|None=None; path_selected: str|None=None; path_executed: str|None=None
    realized_credit: float=0.0; realized_debit: float=0.0; net_cash_flow: float=0.0
    net_campaign_basis: float|None=None; campaign_recovered_pct: float|None=None; campaign_cycle_count: int|None=None
    current_profit_percent: float|None=None; future_roll_score_at_decision: float|None=None
    flip_quality_score_at_decision: float|None=None; collapse_quality_score_at_decision: float|None=None
    regime_at_decision: str|None=None; deployment_label: str|None=None
    risk_envelope: str|None=None; maturity_level: str|None=None
    notes: list[str]=field(default_factory=list); metadata: dict[str,Any]=field(default_factory=dict)

@dataclass(slots=True)
class CampaignTradeRecord:
    campaign_id: str; symbol: str; campaign_family: str; entry_family: str
    opened_utc: str; closed_utc: str|None=None; status: CampaignStatus="OPEN"
    current_structure: str|None=None; current_side: str|None=None
    opening_debit: float=0.0; opening_credit: float=0.0
    realized_credit_collected: float=0.0; realized_close_cost: float=0.0; repair_debit_paid: float=0.0
    net_campaign_basis: float=0.0; campaign_recovered_pct: float=0.0; campaign_cycle_count: int=0
    campaign_realized_pnl: float=0.0; campaign_unrealized_pnl: float=0.0
    path_recommended_last: str|None=None; path_selected_last: str|None=None; path_executed_last: str|None=None
    max_profit_percent_seen: float|None=None; max_drawdown_percent_seen: float|None=None
    entry_regime: str|None=None; last_regime: str|None=None
    deployment_label_last: str|None=None; risk_envelope_last: str|None=None; maturity_level_last: str|None=None
    events: list[CampaignTradeEvent]=field(default_factory=list)

def _utcnow(): return datetime.utcnow().isoformat()
def _rm(v): return round(float(v or 0.0),6)
def _safe_max(a,b):
    if b is None: return a
    if a is None: return float(b)
    return max(float(a),float(b))
def _safe_min(a,b):
    if b is None: return a
    if a is None: return float(b)
    return min(float(a),float(b))

def initialize_campaign_trade_record(campaign_id: str, symbol: str, campaign_family: str,
                                      entry_family: str, opened_utc: str|None=None,
                                      current_structure: str|None=None, current_side: str|None=None,
                                      entry_regime: str|None=None) -> CampaignTradeRecord:
    return CampaignTradeRecord(campaign_id=campaign_id,symbol=symbol,campaign_family=campaign_family,
        entry_family=entry_family,opened_utc=opened_utc or _utcnow(),current_structure=current_structure,
        current_side=current_side,entry_regime=entry_regime,last_regime=entry_regime)

def build_campaign_trade_event(event_id: str, campaign_id: str, event_type: CampaignEventType,
                                symbol: str, campaign_family: str, entry_family: str,
                                transition_family: str|None=None, timestamp_utc: str|None=None,
                                path_recommended: str|None=None, path_selected: str|None=None,
                                path_executed: str|None=None, realized_credit: float=0.0,
                                realized_debit: float=0.0, net_campaign_basis: float|None=None,
                                campaign_recovered_pct: float|None=None, campaign_cycle_count: int|None=None,
                                current_profit_percent: float|None=None,
                                future_roll_score_at_decision: float|None=None,
                                flip_quality_score_at_decision: float|None=None,
                                collapse_quality_score_at_decision: float|None=None,
                                regime_at_decision: str|None=None, deployment_label: str|None=None,
                                risk_envelope: str|None=None, maturity_level: str|None=None,
                                notes: list[str]|None=None, metadata: dict[str,Any]|None=None) -> CampaignTradeEvent:
    rc=_rm(realized_credit); rd=_rm(realized_debit)
    return CampaignTradeEvent(event_id=event_id,campaign_id=campaign_id,timestamp_utc=timestamp_utc or _utcnow(),
        event_type=event_type,symbol=symbol,campaign_family=campaign_family,entry_family=entry_family,
        transition_family=transition_family,path_recommended=path_recommended,path_selected=path_selected,
        path_executed=path_executed,realized_credit=rc,realized_debit=rd,net_cash_flow=round(rc-rd,6),
        net_campaign_basis=net_campaign_basis,campaign_recovered_pct=campaign_recovered_pct,
        campaign_cycle_count=campaign_cycle_count,current_profit_percent=current_profit_percent,
        future_roll_score_at_decision=future_roll_score_at_decision,
        flip_quality_score_at_decision=flip_quality_score_at_decision,
        collapse_quality_score_at_decision=collapse_quality_score_at_decision,
        regime_at_decision=regime_at_decision,deployment_label=deployment_label,
        risk_envelope=risk_envelope,maturity_level=maturity_level,
        notes=list(notes or []),metadata=dict(metadata or {}))

def append_campaign_trade_event(record: CampaignTradeRecord, event: CampaignTradeEvent,
                                 current_structure: str|None=None, current_side: str|None=None,
                                 campaign_unrealized_pnl: float|None=None) -> CampaignTradeRecord:
    events=[*record.events,event]
    od=record.opening_debit; oc=record.opening_credit
    rcc=_rm(record.realized_credit_collected+event.realized_credit)
    rcc_adj=rcc; rc_cost=record.realized_close_cost; rp=record.repair_debit_paid
    if event.event_type=="OPEN_ENTRY":
        od=_rm(od+event.realized_debit); oc=_rm(oc+event.realized_credit)
        rcc_adj=_rm(rcc-event.realized_credit)  # don't double-count opening credit in rcc
    elif event.event_type in("ROLL_SAME_SIDE","FLIP_SELECTIVELY","COLLAPSE_TO_SPREAD","CLOSE","BANK_AND_REDUCE"):
        rc_cost=_rm(rc_cost+event.realized_debit)
    elif event.event_type=="DEFENSIVE_ROLL":
        rp=_rm(rp+max(0.0,event.realized_debit-event.realized_credit))
    # For OPEN_ENTRY, don't accumulate the opening credit into rcc
    rcc_final=rcc_adj if event.event_type=="OPEN_ENTRY" else rcc

    if event.net_campaign_basis is not None:
        ncb=_rm(event.net_campaign_basis)
    else:
        ncb=_rm(od-oc-rcc_final+rc_cost+rp)
    if event.campaign_recovered_pct is not None:
        crp=round(float(event.campaign_recovered_pct),6)
    else:
        base=max(0.01,od-oc); crp=round(max(0.0,min(100.0,100.0*(base-max(0.0,ncb))/base)),6)
    cyc=(int(event.campaign_cycle_count) if event.campaign_cycle_count is not None
         else record.campaign_cycle_count+(1 if event.campaign_cycle_count is None
         and event.event_type in("HARVEST","ROLL_SAME_SIDE","FLIP_SELECTIVELY","COLLAPSE_TO_SPREAD") else 0))
    pnl=round(oc+rcc_final-od-rc_cost-rp,6)
    status=record.status; closed_utc=record.closed_utc
    if event.event_type=="OPEN_ENTRY": status="ACTIVE"
    elif event.event_type=="BANK_AND_REDUCE": status="REDUCED"
    elif event.event_type=="CLOSE": status="CLOSED"; closed_utc=event.timestamp_utc
    return CampaignTradeRecord(campaign_id=record.campaign_id,symbol=record.symbol,
        campaign_family=record.campaign_family,entry_family=record.entry_family,
        opened_utc=record.opened_utc,closed_utc=closed_utc,status=status,
        current_structure=current_structure or record.current_structure,
        current_side=current_side or record.current_side,
        opening_debit=od,opening_credit=oc,realized_credit_collected=rcc_final,
        realized_close_cost=rc_cost,repair_debit_paid=rp,
        net_campaign_basis=ncb,campaign_recovered_pct=crp,campaign_cycle_count=cyc,
        campaign_realized_pnl=pnl,
        campaign_unrealized_pnl=_rm(campaign_unrealized_pnl if campaign_unrealized_pnl is not None else record.campaign_unrealized_pnl),
        path_recommended_last=event.path_recommended or record.path_recommended_last,
        path_selected_last=event.path_selected or record.path_selected_last,
        path_executed_last=event.path_executed or record.path_executed_last,
        max_profit_percent_seen=_safe_max(record.max_profit_percent_seen,event.current_profit_percent),
        max_drawdown_percent_seen=_safe_min(record.max_drawdown_percent_seen,event.current_profit_percent),
        entry_regime=record.entry_regime,last_regime=event.regime_at_decision or record.last_regime,
        deployment_label_last=event.deployment_label or record.deployment_label_last,
        risk_envelope_last=event.risk_envelope or record.risk_envelope_last,
        maturity_level_last=event.maturity_level or record.maturity_level_last,events=events)

def log_open_entry(record: CampaignTradeRecord, event_id: str, realized_debit: float,
                    realized_credit: float=0.0, path_recommended: str|None=None,
                    path_selected: str|None=None, path_executed: str|None=None,
                    regime_at_decision: str|None=None, deployment_label: str|None=None,
                    risk_envelope: str|None=None, maturity_level: str|None=None,
                    notes: list[str]|None=None, metadata: dict[str,Any]|None=None) -> CampaignTradeRecord:
    ev=build_campaign_trade_event(event_id,record.campaign_id,"OPEN_ENTRY",record.symbol,
        record.campaign_family,record.entry_family,path_recommended=path_recommended,
        path_selected=path_selected,path_executed=path_executed,realized_credit=realized_credit,
        realized_debit=realized_debit,regime_at_decision=regime_at_decision,
        deployment_label=deployment_label,risk_envelope=risk_envelope,maturity_level=maturity_level,
        notes=notes,metadata=metadata)
    return append_campaign_trade_event(record,ev)

def log_campaign_transition(record: CampaignTradeRecord, event_id: str, event_type: CampaignEventType,
                             transition_family: str|None=None, realized_credit: float=0.0, realized_debit: float=0.0,
                             path_recommended: str|None=None, path_selected: str|None=None, path_executed: str|None=None,
                             net_campaign_basis: float|None=None, campaign_recovered_pct: float|None=None,
                             campaign_cycle_count: int|None=None, current_profit_percent: float|None=None,
                             future_roll_score_at_decision: float|None=None, flip_quality_score_at_decision: float|None=None,
                             collapse_quality_score_at_decision: float|None=None, regime_at_decision: str|None=None,
                             deployment_label: str|None=None, risk_envelope: str|None=None, maturity_level: str|None=None,
                             current_structure: str|None=None, current_side: str|None=None,
                             campaign_unrealized_pnl: float|None=None,
                             notes: list[str]|None=None, metadata: dict[str,Any]|None=None) -> CampaignTradeRecord:
    ev=build_campaign_trade_event(event_id,record.campaign_id,event_type,record.symbol,
        record.campaign_family,record.entry_family,transition_family,path_recommended=path_recommended,
        path_selected=path_selected,path_executed=path_executed,realized_credit=realized_credit,
        realized_debit=realized_debit,net_campaign_basis=net_campaign_basis,
        campaign_recovered_pct=campaign_recovered_pct,campaign_cycle_count=campaign_cycle_count,
        current_profit_percent=current_profit_percent,future_roll_score_at_decision=future_roll_score_at_decision,
        flip_quality_score_at_decision=flip_quality_score_at_decision,
        collapse_quality_score_at_decision=collapse_quality_score_at_decision,
        regime_at_decision=regime_at_decision,deployment_label=deployment_label,
        risk_envelope=risk_envelope,maturity_level=maturity_level,notes=notes,metadata=metadata)
    return append_campaign_trade_event(record,ev,current_structure,current_side,campaign_unrealized_pnl)

def log_close_campaign(record: CampaignTradeRecord, event_id: str, realized_credit: float=0.0,
                        realized_debit: float=0.0, path_recommended: str|None=None,
                        path_selected: str|None=None, path_executed: str|None=None,
                        net_campaign_basis: float|None=None, campaign_recovered_pct: float|None=None,
                        campaign_cycle_count: int|None=None, current_profit_percent: float|None=None,
                        regime_at_decision: str|None=None, deployment_label: str|None=None,
                        risk_envelope: str|None=None, maturity_level: str|None=None,
                        notes: list[str]|None=None, metadata: dict[str,Any]|None=None) -> CampaignTradeRecord:
    return log_campaign_transition(record,event_id,"CLOSE","FINAL_CLOSE",realized_credit,realized_debit,
        path_recommended,path_selected,path_executed,net_campaign_basis,campaign_recovered_pct,
        campaign_cycle_count,current_profit_percent,regime_at_decision=regime_at_decision,
        deployment_label=deployment_label,risk_envelope=risk_envelope,maturity_level=maturity_level,
        current_structure=record.current_structure,current_side=record.current_side,
        campaign_unrealized_pnl=0.0,notes=notes,metadata=metadata)

def build_campaign_trade_summary(record: CampaignTradeRecord) -> dict[str,Any]:
    return {"campaign_id":record.campaign_id,"symbol":record.symbol,"campaign_family":record.campaign_family,
            "entry_family":record.entry_family,"status":record.status,"opened_utc":record.opened_utc,
            "closed_utc":record.closed_utc,"opening_debit":round(record.opening_debit,6),
            "opening_credit":round(record.opening_credit,6),
            "realized_credit_collected":round(record.realized_credit_collected,6),
            "realized_close_cost":round(record.realized_close_cost,6),
            "repair_debit_paid":round(record.repair_debit_paid,6),
            "net_campaign_basis":round(record.net_campaign_basis,6),
            "campaign_recovered_pct":round(record.campaign_recovered_pct,6),
            "campaign_cycle_count":int(record.campaign_cycle_count),
            "campaign_realized_pnl":round(record.campaign_realized_pnl,6),
            "campaign_unrealized_pnl":round(record.campaign_unrealized_pnl,6),
            "path_recommended_last":record.path_recommended_last,
            "path_selected_last":record.path_selected_last,"path_executed_last":record.path_executed_last,
            "max_profit_percent_seen":record.max_profit_percent_seen,
            "max_drawdown_percent_seen":record.max_drawdown_percent_seen,
            "entry_regime":record.entry_regime,"last_regime":record.last_regime,
            "deployment_label_last":record.deployment_label_last,
            "risk_envelope_last":record.risk_envelope_last,"maturity_level_last":record.maturity_level_last,
            "event_count":len(record.events)}

def campaign_trade_events_to_dicts(record: CampaignTradeRecord) -> list[dict[str,Any]]:
    return [{"event_id":e.event_id,"campaign_id":e.campaign_id,"timestamp_utc":e.timestamp_utc,
             "event_type":e.event_type,"symbol":e.symbol,"campaign_family":e.campaign_family,
             "entry_family":e.entry_family,"transition_family":e.transition_family,
             "path_recommended":e.path_recommended,"path_selected":e.path_selected,"path_executed":e.path_executed,
             "realized_credit":round(e.realized_credit,6),"realized_debit":round(e.realized_debit,6),
             "net_cash_flow":round(e.net_cash_flow,6),"net_campaign_basis":e.net_campaign_basis,
             "campaign_recovered_pct":e.campaign_recovered_pct,"campaign_cycle_count":e.campaign_cycle_count,
             "current_profit_percent":e.current_profit_percent,
             "future_roll_score_at_decision":e.future_roll_score_at_decision,
             "flip_quality_score_at_decision":e.flip_quality_score_at_decision,
             "collapse_quality_score_at_decision":e.collapse_quality_score_at_decision,
             "regime_at_decision":e.regime_at_decision,"deployment_label":e.deployment_label,
             "risk_envelope":e.risk_envelope,"maturity_level":e.maturity_level,
             "notes":e.notes,"metadata":e.metadata} for e in record.events]
