"""doctrine/charter_builder.py — Builds the formal operating charter."""
from __future__ import annotations
from typing import Any
from datetime import datetime
import uuid
from doctrine.principle_catalog import PRINCIPLE_CATALOG, DEFAULT_TRADEOFF_ORDER

def build_operating_charter(title: str="Options AI Assistant Operating Charter",
                              active_principles: list[str]|None=None,
                              tradeoff_order: list[str]|None=None,
                              scope: dict[str,Any]|None=None) -> dict[str,Any]:
    return {"charter_id":str(uuid.uuid4()),"title":title,
            "active_principles":active_principles or list(PRINCIPLE_CATALOG.keys()),
            "tradeoff_order":tradeoff_order or DEFAULT_TRADEOFF_ORDER,
            "scope":scope or {"environments":["DEV","SIM","LIVE"]},
            "effective_utc":datetime.utcnow().isoformat(),"status":"ACTIVE"}
