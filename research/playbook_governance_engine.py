"""research/playbook_governance_engine.py — Safety layer: weak samples can't over-control."""
from __future__ import annotations
from typing import Any

MIN_SAMPLE_FOR_STRONG_BIAS = 5

def apply_playbook_governance(policy_registry, playbook_rankings) -> dict[str,Any]:
    governed={}
    for code,policy in policy_registry.get("playbook_policy_registry",{}).items():
        rd=playbook_rankings.get("rankings",{}).get(code,{})
        n=int(rd.get("count",0)); status=policy.get("status","WATCHLIST")
        qb=float(policy.get("queue_bias",0.0))
        if n < MIN_SAMPLE_FOR_STRONG_BIAS:
            qb=max(-2.0,min(2.0,qb))
            if status in ("DEMOTED","PROMOTED"): status="WATCHLIST"
        governed[code]={**policy,"status":status,"queue_bias":round(qb,2),"sample_count":n}
    return {"governed_playbook_policy_registry":governed}
