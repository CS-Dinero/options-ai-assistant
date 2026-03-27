"""risk/capital_budget_engine.py — Defines available deployable budget."""
from __future__ import annotations
from typing import Any

def build_capital_budget(account_state: dict[str,Any]) -> dict[str,Any]:
    def _sf(k): 
        try: return float(account_state.get(k,0))
        except: return 0.0
    total=_sf("total_equity"); reserved=_sf("reserved_capital"); committed=_sf("committed_risk")
    deployable=max(0.0,total-reserved); available=max(0.0,deployable-committed)
    return {"total_equity":round(total,2),"reserved_capital":round(reserved,2),
            "deployable_capital":round(deployable,2),"committed_risk":round(committed,2),
            "available_incremental_risk":round(available,2)}
