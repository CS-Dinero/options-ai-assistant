"""campaigns/campaign_basis_ledger.py — Single source of truth for campaign economics."""
from __future__ import annotations
from dataclasses import dataclass, field, replace
from typing import Literal
import math

CampaignEventType = Literal[
    "OPEN_ENTRY","HARVEST_CREDIT","CLOSE_COST","REPAIR_DEBIT",
    "ROLL_EVENT","FLIP_EVENT","COLLAPSE_EVENT","FINAL_CLOSE",
]

@dataclass(slots=True)
class CampaignLedgerEvent:
    event_id: str; campaign_id: str; event_type: CampaignEventType; timestamp_utc: str
    debit: float=0.0; credit: float=0.0
    structure_before: str|None=None; structure_after: str|None=None
    side_before: str|None=None; side_after: str|None=None
    notes: str=""; metadata: dict=field(default_factory=dict)

@dataclass(slots=True)
class CampaignLedger:
    campaign_id: str; campaign_family: str; entry_family: str; opened_utc: str
    opening_debit: float=0.0; opening_credit: float=0.0
    realized_credit_collected: float=0.0; realized_close_cost: float=0.0
    repair_debit_paid: float=0.0; campaign_cycle_count: int=0
    campaign_realized_pnl: float=0.0
    current_structure: str|None=None; current_side: str|None=None
    events: list[CampaignLedgerEvent]=field(default_factory=list)

@dataclass(slots=True)
class CampaignLedgerSnapshot:
    campaign_id: str; campaign_family: str; entry_family: str
    opening_debit: float; opening_credit: float
    realized_credit_collected: float; realized_close_cost: float; repair_debit_paid: float
    net_campaign_basis: float; campaign_recovered_pct: float
    campaign_cycle_count: int; campaign_realized_pnl: float
    current_structure: str|None; current_side: str|None

def _safe_money(v: float) -> float:
    if math.isnan(v) or math.isinf(v): raise ValueError(f"Invalid monetary value: {v}")
    return round(float(v), 6)

def _append_event(ledger: CampaignLedger, event: CampaignLedgerEvent) -> CampaignLedger:
    out=replace(ledger, events=[*ledger.events, event])
    out.campaign_realized_pnl=compute_campaign_realized_pnl(out)
    return out

def initialize_campaign_ledger(campaign_id:str, campaign_family:str, entry_family:str,
                                opened_utc:str, current_structure:str|None=None,
                                current_side:str|None=None) -> CampaignLedger:
    return CampaignLedger(campaign_id=campaign_id, campaign_family=campaign_family,
                           entry_family=entry_family, opened_utc=opened_utc,
                           current_structure=current_structure, current_side=current_side)

def apply_opening_entry(ledger:CampaignLedger, event_id:str, timestamp_utc:str,
                         opening_debit:float, opening_credit:float, structure:str, side:str,
                         notes:str="", metadata:dict|None=None) -> CampaignLedger:
    if ledger.events: raise ValueError("Opening entry already applied for this campaign.")
    out=replace(ledger, opening_debit=_safe_money(opening_debit),
                opening_credit=_safe_money(opening_credit),
                current_structure=structure, current_side=side)
    return _append_event(out, CampaignLedgerEvent(event_id=event_id, campaign_id=ledger.campaign_id,
        event_type="OPEN_ENTRY", timestamp_utc=timestamp_utc, debit=out.opening_debit,
        credit=out.opening_credit, structure_after=structure, side_after=side,
        notes=notes, metadata=metadata or {}))

def apply_harvest_credit(ledger:CampaignLedger, event_id:str, timestamp_utc:str,
                          credit_collected:float, structure_after:str|None=None,
                          side_after:str|None=None, notes:str="", metadata:dict|None=None) -> CampaignLedger:
    credit=_safe_money(credit_collected)
    out=replace(ledger, realized_credit_collected=_safe_money(ledger.realized_credit_collected+credit),
                campaign_cycle_count=ledger.campaign_cycle_count+1,
                current_structure=structure_after or ledger.current_structure,
                current_side=side_after or ledger.current_side)
    return _append_event(out, CampaignLedgerEvent(event_id=event_id, campaign_id=ledger.campaign_id,
        event_type="HARVEST_CREDIT", timestamp_utc=timestamp_utc, credit=credit,
        structure_before=ledger.current_structure, structure_after=out.current_structure,
        side_before=ledger.current_side, side_after=out.current_side, notes=notes, metadata=metadata or {}))

def apply_close_cost(ledger:CampaignLedger, event_id:str, timestamp_utc:str, close_cost:float,
                      structure_after:str|None=None, side_after:str|None=None,
                      notes:str="", metadata:dict|None=None) -> CampaignLedger:
    debit=_safe_money(close_cost)
    out=replace(ledger, realized_close_cost=_safe_money(ledger.realized_close_cost+debit),
                current_structure=structure_after or ledger.current_structure,
                current_side=side_after or ledger.current_side)
    return _append_event(out, CampaignLedgerEvent(event_id=event_id, campaign_id=ledger.campaign_id,
        event_type="CLOSE_COST", timestamp_utc=timestamp_utc, debit=debit,
        structure_before=ledger.current_structure, structure_after=out.current_structure,
        side_before=ledger.current_side, side_after=out.current_side, notes=notes, metadata=metadata or {}))

def apply_repair_debit(ledger:CampaignLedger, event_id:str, timestamp_utc:str, repair_debit:float,
                        structure_after:str|None=None, side_after:str|None=None,
                        notes:str="", metadata:dict|None=None) -> CampaignLedger:
    debit=_safe_money(repair_debit)
    out=replace(ledger, repair_debit_paid=_safe_money(ledger.repair_debit_paid+debit),
                current_structure=structure_after or ledger.current_structure,
                current_side=side_after or ledger.current_side)
    return _append_event(out, CampaignLedgerEvent(event_id=event_id, campaign_id=ledger.campaign_id,
        event_type="REPAIR_DEBIT", timestamp_utc=timestamp_utc, debit=debit,
        structure_before=ledger.current_structure, structure_after=out.current_structure,
        side_before=ledger.current_side, side_after=out.current_side, notes=notes, metadata=metadata or {}))

def _roll_like_event(ledger:CampaignLedger, event_id:str, timestamp_utc:str,
                      event_type:CampaignEventType, close_cost:float, new_credit:float,
                      structure_before:str, structure_after:str, side_before:str, side_after:str,
                      notes:str="", metadata:dict|None=None) -> CampaignLedger:
    debit=_safe_money(close_cost); credit=_safe_money(new_credit)
    out=replace(ledger, realized_close_cost=_safe_money(ledger.realized_close_cost+debit),
                realized_credit_collected=_safe_money(ledger.realized_credit_collected+credit),
                campaign_cycle_count=ledger.campaign_cycle_count+1,
                current_structure=structure_after, current_side=side_after)
    return _append_event(out, CampaignLedgerEvent(event_id=event_id, campaign_id=ledger.campaign_id,
        event_type=event_type, timestamp_utc=timestamp_utc, debit=debit, credit=credit,
        structure_before=structure_before, structure_after=structure_after,
        side_before=side_before, side_after=side_after, notes=notes, metadata=metadata or {}))

def apply_roll_event(ledger,event_id,timestamp_utc,close_cost,new_credit,
                      structure_before,structure_after,side_before,side_after,notes="",metadata=None):
    return _roll_like_event(ledger,event_id,timestamp_utc,"ROLL_EVENT",close_cost,new_credit,
                             structure_before,structure_after,side_before,side_after,notes,metadata)

def apply_flip_event(ledger,event_id,timestamp_utc,close_cost,new_credit,
                      structure_before,structure_after,side_before,side_after,notes="",metadata=None):
    return _roll_like_event(ledger,event_id,timestamp_utc,"FLIP_EVENT",close_cost,new_credit,
                             structure_before,structure_after,side_before,side_after,notes,metadata)

def apply_collapse_event(ledger,event_id,timestamp_utc,close_cost,new_credit,
                          structure_before,structure_after,side_before,side_after,notes="",metadata=None):
    return _roll_like_event(ledger,event_id,timestamp_utc,"COLLAPSE_EVENT",close_cost,new_credit,
                             structure_before,structure_after,side_before,side_after,notes,metadata)

def compute_net_campaign_basis(ledger: CampaignLedger) -> float:
    return round(ledger.opening_debit-ledger.opening_credit
                 -ledger.realized_credit_collected+ledger.realized_close_cost
                 +ledger.repair_debit_paid, 6)

def compute_campaign_recovered_pct(ledger: CampaignLedger) -> float:
    base=max(0.01, ledger.opening_debit-ledger.opening_credit)
    net=max(0.0, compute_net_campaign_basis(ledger))
    return round(max(0.0, min(100.0, 100.0*(base-net)/base)), 4)

def compute_campaign_realized_pnl(ledger: CampaignLedger) -> float:
    return round(ledger.opening_credit+ledger.realized_credit_collected
                 -ledger.opening_debit-ledger.realized_close_cost-ledger.repair_debit_paid, 6)

def build_campaign_ledger_snapshot(ledger: CampaignLedger) -> CampaignLedgerSnapshot:
    return CampaignLedgerSnapshot(
        campaign_id=ledger.campaign_id, campaign_family=ledger.campaign_family,
        entry_family=ledger.entry_family, opening_debit=round(ledger.opening_debit,6),
        opening_credit=round(ledger.opening_credit,6),
        realized_credit_collected=round(ledger.realized_credit_collected,6),
        realized_close_cost=round(ledger.realized_close_cost,6),
        repair_debit_paid=round(ledger.repair_debit_paid,6),
        net_campaign_basis=compute_net_campaign_basis(ledger),
        campaign_recovered_pct=compute_campaign_recovered_pct(ledger),
        campaign_cycle_count=ledger.campaign_cycle_count,
        campaign_realized_pnl=compute_campaign_realized_pnl(ledger),
        current_structure=ledger.current_structure, current_side=ledger.current_side)
