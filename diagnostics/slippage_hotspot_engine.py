"""diagnostics/slippage_hotspot_engine.py — Finds execution quality weak spots."""
from __future__ import annotations
from typing import Any

def find_slippage_hotspots(slippage_model: dict[str,Any]) -> dict[str,Any]:
    def _worst(bucket):
        if not bucket: return None,None
        k=min(bucket.keys(),key=lambda x: bucket[x].get("avg_slippage_dollars",0))
        return k, bucket[k]
    ws,wss = _worst(slippage_model.get("by_symbol",{}))
    ww,wws = _worst(slippage_model.get("by_window",{}))
    wp,wps = _worst(slippage_model.get("by_policy",{}))
    return {"worst_symbol":ws,"worst_symbol_stats":wss,
            "worst_window":ww,"worst_window_stats":wws,
            "worst_policy":wp,"worst_policy_stats":wps}
