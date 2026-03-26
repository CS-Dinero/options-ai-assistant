"""env/environment_policy_loader.py — Loads the correct live policy for an environment."""
from __future__ import annotations
from typing import Any

def load_environment_policy_bundle(policy_registry: list[dict[str,Any]], environment: str) -> dict[str,Any]:
    """LIVE must never accidentally read SIM policy — environment tag enforces separation."""
    candidates=[v for v in policy_registry
                if v.get("status")=="LIVE" and v.get("environment")==environment]
    if not candidates: return {}
    best=max(candidates, key=lambda v: v.get("activated_utc") or "")
    return best.get("policy_bundle",{})
