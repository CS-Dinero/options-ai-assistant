"""campaigns/campaign_metrics_engine.py — Campaign-level analytics fields."""
from __future__ import annotations
from typing import Any

def compute_credit_velocity(realized_credit_collected: float, campaign_cycle_count: int,
                             campaign_duration_days: float) -> float:
    if campaign_duration_days<=0: return 0.0
    return round(realized_credit_collected/max(1,campaign_duration_days)*7,4)

def compute_basis_velocity(net_campaign_basis: float, opening_basis: float,
                            campaign_duration_days: float) -> float:
    if campaign_duration_days<=0 or opening_basis<=0: return 0.0
    basis_reduction=max(0.0,opening_basis-net_campaign_basis)
    return round(basis_reduction/max(1,campaign_duration_days)*7,4)

def compute_campaign_complexity_score(roll_count: int, structure_transitions: int,
                                       current_legs: int, side_changes: int) -> float:
    score=20.0*min(5,roll_count)/5+30.0*min(3,structure_transitions)/3
    score+=25.0*min(4,current_legs)/4+25.0*min(2,side_changes)/2
    return round(min(100.0,score),2)

def build_campaign_metrics(ledger_snapshot: Any, campaign_duration_days: float=0.0,
                            current_legs: int=2, side_changes: int=0) -> dict[str,Any]:
    opened=float(getattr(ledger_snapshot,"opening_debit",0))-float(getattr(ledger_snapshot,"opening_credit",0))
    cc=getattr(ledger_snapshot,"realized_credit_collected",0)
    cyc=getattr(ledger_snapshot,"campaign_cycle_count",0)
    basis=getattr(ledger_snapshot,"net_campaign_basis",opened)
    return {
        "credit_velocity":compute_credit_velocity(float(cc),cyc,campaign_duration_days),
        "basis_velocity":compute_basis_velocity(float(basis),opened,campaign_duration_days),
        "campaign_complexity_score":compute_campaign_complexity_score(cyc,side_changes,current_legs,side_changes),
        "campaign_duration_days":campaign_duration_days,
        "campaign_cycle_count":cyc,
    }
