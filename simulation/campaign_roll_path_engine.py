"""simulation/campaign_roll_path_engine.py — Models repeated roll sequences and dead-end risk."""
from __future__ import annotations
from dataclasses import dataclass, field

@dataclass(slots=True)
class RollCycleSpec:
    roll_credit: float; roll_cost: float; continuity_score: float; cycle_index: int

@dataclass(slots=True)
class RollPathResult:
    opening_debit: float; total_cycles: int; total_credits: float; total_costs: float
    net_basis_final: float; recovered_pct: float; avg_roll_credit: float
    continuity_breaks: int; dead_end_risk: str; cycle_details: list[dict]=field(default_factory=list)

def simulate_roll_path(opening_debit: float, opening_credit: float,
                        roll_cycles: list[RollCycleSpec],
                        min_continuity_score: float=60.0) -> RollPathResult:
    basis=opening_debit-opening_credit; credits=0.0; costs=0.0; breaks=0
    details=[]
    for cyc in roll_cycles:
        net_roll=cyc.roll_credit-cyc.roll_cost
        basis-=net_roll; credits+=cyc.roll_credit; costs+=cyc.roll_cost
        if cyc.continuity_score<min_continuity_score: breaks+=1
        details.append({"cycle":cyc.cycle_index,"net_roll":round(net_roll,4),"basis":round(basis,4),
                        "continuity":cyc.continuity_score,"break":cyc.continuity_score<min_continuity_score})
    base_outlay=max(0.01,opening_debit-opening_credit)
    net_basis_final=basis; rec=round(max(0.0,min(100.0,100.0*(base_outlay-max(0.0,net_basis_final))/base_outlay)),4)
    avg_credit=round(credits/max(1,len(roll_cycles)),4)
    dead_end=("HIGH" if breaks>len(roll_cycles)*0.4 else "MODERATE" if breaks>0 else "LOW")
    return RollPathResult(opening_debit=opening_debit,total_cycles=len(roll_cycles),
                          total_credits=round(credits,4),total_costs=round(costs,4),
                          net_basis_final=round(net_basis_final,4),recovered_pct=rec,
                          avg_roll_credit=avg_credit,continuity_breaks=breaks,
                          dead_end_risk=dead_end,cycle_details=details)
