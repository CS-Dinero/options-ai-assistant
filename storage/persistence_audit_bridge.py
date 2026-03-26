"""storage/persistence_audit_bridge.py — Attaches persistence metadata to audit records."""
from __future__ import annotations
from typing import Any

def attach_persistence_metadata(record: dict[str,Any], repository_name: str) -> dict[str,Any]:
    out=dict(record); out["_repository"]=repository_name; return out
