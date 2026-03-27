"""command/priority_stack_engine.py — Ranks what matters most right now."""
from __future__ import annotations
from typing import Any

BAND_ORDER={"ACT_NOW":0,"DECIDE_NOW":1,"WATCH_CLOSELY":2,"IMPROVE_LATER":3}

def build_priority_stack(executive_state: dict[str,Any]) -> list[dict[str,Any]]:
    items=[]
    for a in executive_state.get("alerts",[]):
        items.append({"priority_band":"ACT_NOW" if a.get("severity")=="CRITICAL" else "WATCH_CLOSELY",
                      "title":a.get("summary","Alert"),"source_type":"ALERT"})
    for r in executive_state.get("reviews",[]):
        if r.get("priority") in ("P0","P1"):
            items.append({"priority_band":"DECIDE_NOW","title":r.get("title","Urgent review"),"source_type":"REVIEW"})
    for r in executive_state.get("releases",[]):
        if r.get("state") not in ("COMPLETED","CANCELLED"):
            items.append({"priority_band":"WATCH_CLOSELY","title":r.get("title","Release bundle"),"source_type":"RELEASE"})
    items.sort(key=lambda x: BAND_ORDER.get(x["priority_band"],99))
    return items
