"""arch/impact_trace_engine.py — Answers what is downstream of a component change."""
from __future__ import annotations
from typing import Any
from collections import deque
from arch.dependency_engine import DEPENDENCY_MAP

def trace_downstream_impact(component_id: str) -> dict[str,Any]:
    # Build reverse map: child → list of parents that depend on it
    reverse: dict[str,list[str]] = {}
    for parent,children in DEPENDENCY_MAP.items():
        for child in children:
            reverse.setdefault(child,[]).append(parent)

    impacted=[]; q=deque([component_id]); seen=set()
    while q:
        cur=q.popleft()
        if cur in seen: continue
        seen.add(cur)
        for d in reverse.get(cur,[]):
            impacted.append(d); q.append(d)

    return {"component_id":component_id,"downstream_impacted_components":impacted,
            "impact_depth":len(impacted)}

def blast_radius_label(depth: int) -> str:
    if depth==0:   return "ISOLATED"
    if depth<=2:   return "NARROW"
    if depth<=5:   return "MODERATE"
    return "BROAD"
