"""simulation/campaign_path_simulator.py — Simulates full campaign paths across multiple cycles."""
from __future__ import annotations
from typing import Any
from dataclasses import dataclass, field
from campaigns.campaign_basis_ledger import (
    initialize_campaign_ledger, apply_opening_entry, apply_roll_event,
    apply_harvest_credit, apply_close_cost, build_campaign_ledger_snapshot,
)

@dataclass(slots=True)
class CampaignCycleSpec:
    """A single simulated campaign cycle."""
    cycle_type: str          # HARVEST_CREDIT | ROLL | DEFENSIVE_ROLL | FLIP | COLLAPSE | FINAL_CLOSE
    credit_collected: float=0.0
    close_cost: float=0.0
    structure_after: str|None=None
    side_after: str|None=None
    notes: str=""

@dataclass(slots=True)
class CampaignSimResult:
    campaign_id: str
    opening_debit: float
    final_net_basis: float
    final_recovered_pct: float
    total_cycles: int
    total_credits: float
    total_costs: float
    final_pnl: float
    cycle_log: list[dict]=field(default_factory=list)

def simulate_campaign_path(campaign_id: str, campaign_family: str, entry_family: str,
                            opening_debit: float, opening_credit: float,
                            initial_structure: str, initial_side: str,
                            cycles: list[CampaignCycleSpec]) -> CampaignSimResult:
    import uuid
    ledger=initialize_campaign_ledger(campaign_id,campaign_family,entry_family,
                                       "2026-01-01T00:00:00",initial_structure,initial_side)
    ledger=apply_opening_entry(ledger,str(uuid.uuid4()),"2026-01-01T00:00:00",
                                opening_debit,opening_credit,initial_structure,initial_side)
    cycle_log=[]
    for i,cycle in enumerate(cycles):
        eid=str(uuid.uuid4()); ts=f"2026-01-{i+2:02d}T00:00:00"
        if cycle.cycle_type in("ROLL","FLIP","COLLAPSE","DEFENSIVE_ROLL"):
            ledger=apply_roll_event(ledger,eid,ts,cycle.close_cost,cycle.credit_collected,
                                     ledger.current_structure or "",cycle.structure_after or ledger.current_structure or "",
                                     ledger.current_side or "",cycle.side_after or ledger.current_side or "",cycle.notes)
        elif cycle.cycle_type=="HARVEST_CREDIT":
            ledger=apply_harvest_credit(ledger,eid,ts,cycle.credit_collected,
                                         cycle.structure_after,cycle.side_after,cycle.notes)
        elif cycle.cycle_type=="FINAL_CLOSE":
            ledger=apply_close_cost(ledger,eid,ts,cycle.close_cost,
                                     cycle.structure_after,cycle.side_after,cycle.notes)
        snap=build_campaign_ledger_snapshot(ledger)
        cycle_log.append({"cycle":i+1,"type":cycle.cycle_type,"basis":snap.net_campaign_basis,
                           "recovered_pct":snap.campaign_recovered_pct})
    snap=build_campaign_ledger_snapshot(ledger)
    return CampaignSimResult(campaign_id=campaign_id,opening_debit=opening_debit,
                              final_net_basis=snap.net_campaign_basis,
                              final_recovered_pct=snap.campaign_recovered_pct,
                              total_cycles=snap.campaign_cycle_count,
                              total_credits=snap.realized_credit_collected,
                              total_costs=snap.realized_close_cost,
                              final_pnl=snap.campaign_realized_pnl,cycle_log=cycle_log)
