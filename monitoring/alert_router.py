"""monitoring/alert_router.py — Classifies who should see each alert."""
from __future__ import annotations
from typing import Any

def route_alert(alert: dict[str,Any]) -> dict[str,Any]:
    m=alert.get("metric_name","")
    if m in ("avg_fill_score_recent","avg_slippage_recent"):
        audience=["TRADER_OPERATOR","ADMIN"]
    elif m in ("blocked_candidate_rate","surface_block_rate","timing_block_rate","queue_depth"):
        audience=["ANALYST","APPROVER","ADMIN"]
    elif m in ("top_symbol_concentration","capital_block_rate"):
        audience=["APPROVER","ADMIN"]
    else:
        audience=["ANALYST","ADMIN"]
    return {**alert,"audience":audience}
