"""env/environment_audit_bridge.py — Attaches environment context to audit events."""
from __future__ import annotations
from typing import Any

def attach_environment_to_audit_event(audit_event: dict[str,Any], environment: str) -> dict[str,Any]:
    out=dict(audit_event); meta=dict(out.get("metadata",{}))
    meta["environment"]=environment; out["metadata"]=meta; out["environment"]=environment
    return out
