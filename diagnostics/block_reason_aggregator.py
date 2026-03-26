"""diagnostics/block_reason_aggregator.py — Groups why candidates were blocked or delayed."""
from __future__ import annotations
from typing import Any
from collections import Counter, defaultdict

def aggregate_block_reasons(rows: list[dict[str,Any]]) -> dict[str,Any]:
    reason_counter=Counter(); by_symbol=defaultdict(Counter); by_playbook=defaultdict(Counter)
    for row in rows:
        reasons=[]
        if row.get("transition_execution_surface_ok") is False: reasons.append("BLOCKED_SURFACE")
        if row.get("transition_timing_ok") is False:             reasons.append("BLOCKED_TIMING")
        if row.get("transition_portfolio_fit_ok") is False:      reasons.append("BLOCKED_PORTFOLIO")
        if row.get("capital_commitment_ok") is False:            reasons.append("BLOCKED_CAPITAL")
        if not row.get("symbol_concurrency_ok",True) or not row.get("playbook_concurrency_ok",True):
            reasons.append("BLOCKED_CONCURRENCY")
        for r in reasons:
            reason_counter[r]+=1
            by_symbol[row.get("symbol","?")][r]+=1
            by_playbook[row.get("playbook_code","?")][r]+=1
    return {"reason_counts":dict(reason_counter),
            "by_symbol":{k:dict(v) for k,v in by_symbol.items()},
            "by_playbook":{k:dict(v) for k,v in by_playbook.items()}}
