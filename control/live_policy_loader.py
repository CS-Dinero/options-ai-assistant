"""control/live_policy_loader.py — Ensures runtime uses only the currently active approved policy."""
from __future__ import annotations
from typing import Any

def load_live_policy_bundle(registry: list[dict[str,Any]]) -> dict[str,Any]:
    live=[v for v in registry if v.get("status")=="LIVE"]
    if not live: return {}
    latest=max(live, key=lambda v: v.get("activated_utc") or "")
    return latest.get("policy_bundle",{})
