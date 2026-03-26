"""decision/override_analysis_engine.py — Studies system-vs-human divergence patterns."""
from __future__ import annotations
from typing import Any
from collections import Counter, defaultdict

def analyze_operator_overrides(decision_packets: list[dict[str,Any]]) -> dict[str,Any]:
    agreement_counter=Counter(); reason_counter=Counter(); by_playbook=defaultdict(int)
    for d in decision_packets:
        r=d.get("rationale") or {}
        mode=r.get("agreement_mode","UNKNOWN"); reason=r.get("primary_reason_code","UNKNOWN")
        agreement_counter[mode]+=1; reason_counter[reason]+=1
        snap=d.get("system_snapshot") or {}
        if snap.get("playbook_code") and mode=="OVERRIDE":
            by_playbook[snap["playbook_code"]]+=1
    return {"agreement_modes":dict(agreement_counter),
            "primary_reason_counts":dict(reason_counter),
            "override_by_playbook":dict(by_playbook)}
