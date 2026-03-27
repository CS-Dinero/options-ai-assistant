"""review/review_packet_builder.py — Builds review objects with context and evidence."""
from __future__ import annotations
from typing import Any
from datetime import datetime
import uuid

def build_review_packet(review_type: str, environment: str, source_object_id: str,
                         source_object_type: str, title: str, summary: str,
                         evidence: dict[str,Any], recommended_question: str) -> dict[str,Any]:
    return {"review_id":str(uuid.uuid4()),"review_type":review_type,"environment":environment,
            "source_object_id":source_object_id,"source_object_type":source_object_type,
            "title":title,"summary":summary,"evidence":evidence,
            "recommended_question":recommended_question,
            "created_utc":datetime.utcnow().isoformat(),
            "priority":"NORMAL","assigned_role":None,"state":"OPEN","resolution":None}
