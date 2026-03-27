"""causal/intervention_catalog.py — Explicit intervention records."""
from __future__ import annotations
from typing import Any
from datetime import datetime
import uuid

def build_intervention_record(intervention_type: str, environment: str, object_id: str,
                               title: str, target_scope: dict[str,Any],
                               effective_utc: str|None=None, metadata: dict[str,Any]|None=None) -> dict[str,Any]:
    return {"intervention_id":str(uuid.uuid4()),"intervention_type":intervention_type,
            "environment":environment,"object_id":object_id,"title":title,"target_scope":target_scope,
            "effective_utc":effective_utc or datetime.utcnow().isoformat(),"metadata":metadata or {}}
