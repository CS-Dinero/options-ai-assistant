"""execution/slippage_model.py — Aggregates execution behavior by symbol/action/window/policy."""
from __future__ import annotations
from typing import Any
from collections import defaultdict

def build_slippage_model(entries: list[dict[str,Any]]) -> dict[str,Any]:
    buckets = {k: defaultdict(list) for k in ("symbol","action","window","policy","rebuild")}
    for e in entries:
        sv=(float(e.get("slippage_dollars",0)), float(e.get("fill_score",0)))
        for k,field in [("symbol","symbol"),("action","action"),("window","time_window"),
                        ("policy","execution_policy"),("rebuild","rebuild_class")]:
            if e.get(field): buckets[k][e[field]].append(sv)
    def _s(bkt):
        out={}
        for key,vals in bkt.items():
            out[key]={"count":len(vals),
                      "avg_slippage_dollars":round(sum(v[0] for v in vals)/len(vals),3),
                      "avg_fill_score":round(sum(v[1] for v in vals)/len(vals),2)}
        return out
    return {f"by_{k}": _s(v) for k,v in buckets.items()}
