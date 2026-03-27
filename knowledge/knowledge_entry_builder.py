"""knowledge/knowledge_entry_builder.py — Creates governed memory entries."""
from __future__ import annotations
from typing import Any
from datetime import datetime
import uuid

def build_knowledge_entry(environment: str, knowledge_type: str, source_family: str,
                           source_object_ids: list[str], subject_type: str, subject_id: str,
                           summary: str, details: dict[str,Any], tags: list[str]|None=None,
                           confidence: str="MEDIUM", status: str="ACTIVE") -> dict[str,Any]:
    return {"knowledge_id":str(uuid.uuid4()),"environment":environment,
            "knowledge_type":knowledge_type,"status":status,"confidence":confidence,
            "source_family":source_family,"source_object_ids":source_object_ids,
            "subject_type":subject_type,"subject_id":subject_id,
            "summary":summary,"details":details,"tags":tags or [],
            "created_utc":datetime.utcnow().isoformat()}
