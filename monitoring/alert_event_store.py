"""monitoring/alert_event_store.py — Stores alert history."""
from __future__ import annotations
from typing import Any

def append_alerts(store: list[dict[str,Any]], new: list[dict[str,Any]]) -> list[dict[str,Any]]:
    return list(store or []) + new
