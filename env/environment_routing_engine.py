"""env/environment_routing_engine.py — Tags objects with environment and applies prefixes."""
from __future__ import annotations
from typing import Any

def apply_environment_routing_prefix(environment: str, object_id: str) -> str:
    return f"{environment}_{object_id}"

def tag_object_with_environment(obj: dict[str,Any], environment: str) -> dict[str,Any]:
    out=dict(obj); out["environment"]=environment; return out
