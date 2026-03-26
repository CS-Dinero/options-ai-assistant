"""diagnostics/policy_pressure_engine.py — Measures how policy overlays affect live outcomes."""
from __future__ import annotations
from typing import Any
from collections import defaultdict

def analyze_policy_pressure(rows: list[dict[str,Any]]) -> dict[str,Any]:
    bias_sum=0.0; capital_blocks=0; reduced=0; by_status=defaultdict(int)
    for r in rows:
        bias_sum += float(r.get("playbook_queue_bias",0))
        if r.get("capital_commitment_decision")=="BLOCK_EXPANSION": capital_blocks+=1
        if r.get("capital_commitment_decision")=="ALLOW_REDUCED":   reduced+=1
        by_status[r.get("playbook_status","?")]+=1
    return {"total_queue_bias":round(bias_sum,2),"capital_blocks":capital_blocks,
            "reduced_commitment_count":reduced,"by_playbook_status":dict(by_status)}
