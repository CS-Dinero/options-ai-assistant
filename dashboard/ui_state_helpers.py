"""dashboard/ui_state_helpers.py — Row filtering utilities for cockpit subsets."""
from __future__ import annotations

def filter_ready_now(rows): return [r for r in rows if r.get("transition_execution_policy")=="FULL_NOW"]
def filter_stagger(rows):   return [r for r in rows if r.get("transition_execution_policy")=="STAGGER"]
def filter_delay(rows):     return [r for r in rows if r.get("transition_execution_policy")=="DELAY"]
def filter_near_zero_basis(rows): return [r for r in rows if float(r.get("campaign_net_basis",9999))<=0.5]
def filter_basis_trapped(rows):
    return [r for r in rows if float(r.get("campaign_recovered_pct",0))<25 and int(r.get("campaign_harvest_cycles",0))>=2]
def filter_high_priority(rows): return [r for r in rows if str(r.get("bot_priority","P6")) in ("P0","P1","P2")]

def build_operational_tags(row: dict) -> list[str]:
    tags=[]
    pol=row.get("transition_execution_policy","")
    if pol=="FULL_NOW":  tags.append("READY_NOW")
    elif pol=="STAGGER": tags.append("STAGGER")
    elif pol=="DELAY":   tags.append("DELAY")
    if row.get("transition_execution_surface_ok") is False: tags.append("BLOCKED_SURFACE")
    if row.get("transition_timing_ok") is False:             tags.append("BLOCKED_TIMING")
    if row.get("transition_portfolio_fit_ok") is False:      tags.append("BLOCKED_PORTFOLIO")
    if float(row.get("campaign_net_basis",9999))<=0.5:       tags.append("NEAR_ZERO_BASIS")
    if float(row.get("campaign_recovered_pct",0))<25 and int(row.get("campaign_harvest_cycles",0))>=2:
        tags.append("TRAPPED_BASIS")
    if str(row.get("bot_priority","P6")) in ("P0","P1","P2"): tags.append("HIGH_PRIORITY")
    if float(row.get("transition_latest_fill_score",100))<60: tags.append("FILL_CAUTION")
    return tags
