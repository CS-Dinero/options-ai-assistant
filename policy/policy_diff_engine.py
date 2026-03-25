"""policy/policy_diff_engine.py — Compares baseline vs simulated queue and capital state."""
from __future__ import annotations
from typing import Any

def _sf(v,d=0.0):
    try: return float(v) if v not in(None,"") else d
    except: return d

def build_policy_diff(
    baseline_queue: list[dict[str,Any]], simulated_queue: list[dict[str,Any]],
    baseline_rows:  list[dict[str,Any]], simulated_rows:  list[dict[str,Any]],
) -> dict[str,Any]:
    bq={str(r.get("position_id","")): r for r in baseline_queue}
    sq={str(r.get("position_id","")): r for r in simulated_queue}
    moved=[]; removed=[]; added=[]
    for pid,bi in bq.items():
        si=sq.get(pid)
        if si:
            delta=_sf(si.get("queue_score"))-_sf(bi.get("queue_score"))
            if abs(delta)>=1.0:
                moved.append({"position_id":pid,"symbol":bi.get("symbol"),
                              "baseline_score":_sf(bi.get("queue_score")),
                              "sim_score":_sf(si.get("queue_score")),"delta":round(delta,2)})
        else: removed.append({"position_id":pid,"symbol":bi.get("symbol"),"reason":"removed from sim queue"})
    for pid,si in sq.items():
        if pid not in bq: added.append({"position_id":pid,"symbol":si.get("symbol"),"reason":"new in sim queue"})

    br={str(r.get("trade_id") or r.get("id","")): r for r in baseline_rows}
    sr={str(r.get("trade_id") or r.get("id","")): r for r in simulated_rows}
    changes=[]
    for pid,b in br.items():
        s=sr.get(pid)
        if not s: continue
        if (b.get("capital_commitment_decision")!=s.get("capital_commitment_decision") or
            b.get("transition_final_contract_add")!=s.get("transition_final_contract_add") or
            b.get("transition_execution_policy")!=s.get("transition_execution_policy")):
            changes.append({"position_id":pid,"symbol":b.get("symbol"),
                "baseline_commitment":b.get("capital_commitment_decision"),
                "sim_commitment":s.get("capital_commitment_decision"),
                "baseline_add":b.get("transition_final_contract_add"),
                "sim_add":s.get("transition_final_contract_add"),
                "baseline_policy":b.get("transition_execution_policy"),
                "sim_policy":s.get("transition_execution_policy")})
    return {"queue_movers":moved,"queue_removed":removed,"queue_added":added,"commitment_changes":changes}
