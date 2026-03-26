"""control/control_plane_audit_log.py — Append-only audit trail for all privileged actions."""
from __future__ import annotations
from typing import Any
from datetime import datetime
import uuid

def build_control_plane_event(event_type: str, actor: str, object_id: str,
                               summary: str, metadata: dict[str,Any]|None=None) -> dict[str,Any]:
    return {"event_id":str(uuid.uuid4()),"event_type":event_type,"actor":actor,
            "object_id":object_id,"summary":summary,"metadata":metadata or {},
            "timestamp_utc":datetime.utcnow().isoformat()}

def append_control_plane_event(audit_log: list[dict[str,Any]],
                                event: dict[str,Any]) -> list[dict[str,Any]]:
    return list(audit_log or []) + [event]
