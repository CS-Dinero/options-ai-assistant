"""command/attention_router.py — Groups issues by executive action type."""
from __future__ import annotations
from typing import Any

def route_attention(priority_stack: list[dict[str,Any]]) -> dict[str,Any]:
    routed={"RISK_ACTIONS":[],"APPROVAL_ACTIONS":[],"RELEASE_ACTIONS":[],"INVESTIGATION_ACTIONS":[]}
    for item in priority_stack:
        st=item.get("source_type")
        if st=="ALERT":    routed["RISK_ACTIONS"].append(item)
        elif st=="REVIEW": routed["APPROVAL_ACTIONS"].append(item)
        elif st=="RELEASE":routed["RELEASE_ACTIONS"].append(item)
        else:              routed["INVESTIGATION_ACTIONS"].append(item)
    return routed
