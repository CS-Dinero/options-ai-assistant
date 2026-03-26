"""diagnostics/playbook_drag_engine.py — Finds playbooks consuming basis but underperforming."""
from __future__ import annotations
from typing import Any

def analyze_playbook_drag(rows: list[dict[str,Any]], playbook_stats: dict[str,Any]) -> dict[str,Any]:
    basis_pb={}; count_pb={}
    for r in rows:
        c=r.get("playbook_code","?"); b=float(r.get("campaign_net_basis",0))
        basis_pb[c]=basis_pb.get(c,0.0)+b; count_pb[c]=count_pb.get(c,0)+1
    stats_map=playbook_stats.get("by_playbook",{})
    drag=[]
    for code,basis in basis_pb.items():
        s=stats_map.get(code,{}); oc=float(s.get("avg_outcome_score",0)); fs=float(s.get("avg_fill_score",0))
        n=count_pb.get(code,0)
        if basis>0 and n>0:
            drag.append({"playbook_code":code,"active_basis":round(basis,2),"active_count":n,
                         "avg_outcome":oc,"avg_fill":fs,
                         "drag_score":round(0.50*basis+0.30*max(0,70-oc)+0.20*max(0,70-fs),2)})
    drag.sort(key=lambda x: x["drag_score"],reverse=True)
    return {"playbook_drag":drag}
