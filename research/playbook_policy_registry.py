"""research/playbook_policy_registry.py — Operational policy per playbook (status + regime + symbol)."""
from __future__ import annotations
from typing import Any

def build_playbook_policy_registry(registry, statuses, regime_dependency, symbol_dependency) -> dict[str,Any]:
    out={}
    STATUS_BIAS={"PROMOTED":4.0,"WATCHLIST":1.0,"LIMITED_USE":-2.0,"DEMOTED":-6.0}
    for code,meta in registry.items():
        status=statuses.get("playbook_statuses",{}).get(code,{}).get("status",meta.get("default_status","WATCHLIST"))
        out[code]={"name":meta.get("name"),"family":meta.get("family"),"status":status,
                   "regime_info":regime_dependency.get("regime_dependency",{}).get(code,{}),
                   "symbol_info":symbol_dependency.get("symbol_dependency",{}).get(code,{}),
                   "queue_bias":STATUS_BIAS.get(status,0.0)}
    return {"playbook_policy_registry":out}
