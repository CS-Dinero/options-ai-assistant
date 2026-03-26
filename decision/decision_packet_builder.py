"""decision/decision_packet_builder.py — Creates decision records tied to review objects."""
from __future__ import annotations
from typing import Any
from datetime import datetime
import uuid

def build_decision_packet(environment: str, actor: str, decision_type: str,
                           source_object_id: str, source_object_type: str,
                           review_id: str|None=None, system_snapshot: dict[str,Any]|None=None) -> dict[str,Any]:
    return {"decision_id":str(uuid.uuid4()),"environment":environment,
            "timestamp_utc":datetime.utcnow().isoformat(),"actor":actor,
            "decision_type":decision_type,"source_object_id":source_object_id,
            "source_object_type":source_object_type,"review_id":review_id,
            "system_snapshot":system_snapshot or {},"rationale":None,"decision_effect":None}
