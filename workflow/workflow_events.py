"""workflow/workflow_events.py — Creates structured lifecycle events."""
from __future__ import annotations
from typing import Any
from datetime import datetime
import uuid

def build_workflow_event(object_type: str, object_id: str, from_state: str, to_state: str,
                          actor: str, note: str="", metadata: dict[str,Any]|None=None) -> dict[str,Any]:
    return {"workflow_event_id":str(uuid.uuid4()),"object_type":object_type,"object_id":object_id,
            "from_state":from_state,"to_state":to_state,"actor":actor,"note":note,
            "metadata":metadata or {},"timestamp_utc":datetime.utcnow().isoformat()}
