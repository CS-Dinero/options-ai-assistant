"""research/playbook_scenario_replayer.py — Filters dataset by playbook/symbol/regime."""
from __future__ import annotations
from typing import Any

def replay_playbook_scenarios(dataset: list[dict[str,Any]], playbook_code=None,
                               symbol=None, regime_filter=None,
                               execution_policy=None, rebuild_class=None) -> list[dict[str,Any]]:
    rf=regime_filter or {}
    out=[]
    for r in dataset:
        if playbook_code and r.get("playbook_code")!=playbook_code: continue
        if symbol        and r.get("symbol")!=symbol: continue
        if execution_policy and r.get("execution_policy")!=execution_policy: continue
        if rebuild_class and r.get("rebuild_class")!=rebuild_class: continue
        if all(r.get(k)==v for k,v in rf.items()): out.append(r)
    return out
