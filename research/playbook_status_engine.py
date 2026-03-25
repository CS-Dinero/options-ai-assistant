"""research/playbook_status_engine.py — Maps ranking into PROMOTED/WATCHLIST/LIMITED_USE/DEMOTED."""
from __future__ import annotations
from typing import Any

def assign_playbook_status(playbook_rankings: dict[str,Any], playbook_stats: dict[str,Any]) -> dict[str,Any]:
    statuses={}
    for code,rd in playbook_rankings.get("rankings",{}).items():
        stats=playbook_stats.get("by_playbook",{}).get(code,{})
        n=int(rd.get("count",0)); rs=float(rd.get("rank_score",0))
        sr=float(stats.get("success_rate",0)); fs=float(stats.get("avg_fill_score",0))
        if   n>=10 and rs>=75 and sr>=0.60 and fs>=65: status="PROMOTED"
        elif rs>=60:  status="WATCHLIST"
        elif n>=5 and rs<55: status="DEMOTED"
        else: status="LIMITED_USE"
        statuses[code]={"status":status,"rank_score":rs,"count":n}
    return {"playbook_statuses":statuses}
