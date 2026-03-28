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


# ═══════════════════════════════════════════════════════════════════════════════
# v2 API — Step-based simulation with RankedPath inputs
# ═══════════════════════════════════════════════════════════════════════════════
from dataclasses import dataclass, field as _field
from typing import Any as _Any

@dataclass(slots=True)
class CampaignSimulationConfig:
    max_cycles: int=12; max_steps: int=10

@dataclass(slots=True)
class CampaignSimulationStepInput:
    step_index: int; timestamp_utc: str; symbol: str
    current_structure: str; current_side: str
    current_profit_percent: float; campaign_unrealized_pnl: float
    execution_surface_score: float; timing_score: float; regime_alignment_score: float
    distance_to_strike: float; expected_move: float; short_dte: int; long_dte: int
    ranked_paths: list=_field(default_factory=list)
    close_cost: float=0.0

@dataclass(slots=True)
class CampaignSimulationResultV2:
    campaign_id: str; step_count: int
    final_ledger_snapshot: _Any  # CampaignLedgerSnapshot
    transition_history: list[dict[str,_Any]]
    final_pnl: float; total_credits: float; total_debits: float

def simulate_campaign_path_v2(campaign_id: str, symbol: str, campaign_family: str,
                               entry_family: str, opening_timestamp_utc: str,
                               opening_structure: str, opening_side: str,
                               opening_debit: float, opening_credit: float,
                               step_inputs: list[CampaignSimulationStepInput],
                               cfg: CampaignSimulationConfig|None=None) -> CampaignSimulationResultV2:
    cfg=cfg or CampaignSimulationConfig()
    import uuid
    ledger=initialize_campaign_ledger(campaign_id,campaign_family,entry_family,opening_timestamp_utc,
                                       opening_structure,opening_side)
    ledger=apply_opening_entry(ledger,str(uuid.uuid4()),opening_timestamp_utc,
                                opening_debit,opening_credit,opening_structure,opening_side)
    history=[]; total_credits=0.0; total_debits=0.0

    for step in step_inputs[:cfg.max_steps]:
        paths=step.ranked_paths
        top=next((p for p in paths if getattr(p,'approved',False)),None) if paths else None

        if top is None:
            # No approved path — defer or close
            action="DEFER_AND_WAIT"
            if step.close_cost>0:
                ledger=apply_close_cost(ledger,str(uuid.uuid4()),step.timestamp_utc,step.close_cost)
                total_debits+=step.close_cost; action="CLOSE"
            snap=build_campaign_ledger_snapshot(ledger)
            history.append({"step":step.step_index,"action":action,"selected_path_code":None,
                             "realized_credit":0.0,"realized_debit":step.close_cost,
                             "net_cash_flow":-step.close_cost,"basis":snap.net_campaign_basis,
                             "recovered_pct":snap.campaign_recovered_pct})
            continue

        path_code=getattr(top,'path_code','DEFER_AND_WAIT')
        credit=float(getattr(top,'projected_credit',0.0))
        debit=float(getattr(top,'projected_debit',0.0))+float(step.close_cost)

        if path_code in("ROLL_SAME_SIDE","FLIP_SELECTIVELY"):
            ledger=apply_roll_event(ledger,str(uuid.uuid4()),step.timestamp_utc,debit,credit,
                                     step.current_structure,step.current_structure,
                                     step.current_side,step.current_side)
        elif path_code=="COLLAPSE_TO_SPREAD":
            ledger=apply_harvest_credit(ledger,str(uuid.uuid4()),step.timestamp_utc,credit-debit)
        elif path_code in("BANK_AND_REDUCE","DEFER_AND_WAIT"):
            if credit>0:
                ledger=apply_harvest_credit(ledger,str(uuid.uuid4()),step.timestamp_utc,credit)
        else:
            if credit>0:
                ledger=apply_harvest_credit(ledger,str(uuid.uuid4()),step.timestamp_utc,credit)

        total_credits+=credit; total_debits+=debit
        snap=build_campaign_ledger_snapshot(ledger)
        history.append({"step":step.step_index,"action":path_code,"selected_path_code":path_code,
                         "realized_credit":credit,"realized_debit":debit,"net_cash_flow":credit-debit,
                         "basis":snap.net_campaign_basis,"recovered_pct":snap.campaign_recovered_pct})

        if snap.campaign_cycle_count>=cfg.max_cycles: break

    final_snap=build_campaign_ledger_snapshot(ledger)
    return CampaignSimulationResultV2(campaign_id=campaign_id,step_count=len(step_inputs),
        final_ledger_snapshot=final_snap,transition_history=history,
        final_pnl=final_snap.campaign_realized_pnl,
        total_credits=round(total_credits,6),total_debits=round(total_debits,6))
