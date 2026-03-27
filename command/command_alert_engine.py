"""command/command_alert_engine.py — Compresses alerts to executive-critical signals."""
from __future__ import annotations
from typing import Any

def build_command_alerts(alerts: list[dict[str,Any]], limit: int=5) -> list[dict[str,Any]]:
    crit=[a for a in alerts if a.get("severity")=="CRITICAL"]
    warn=[a for a in alerts if a.get("severity")=="WARNING"]
    return (crit+warn)[:limit]
