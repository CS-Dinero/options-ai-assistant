"""policy/policy_override_engine.py — Applies hypothetical overrides without mutating live config."""
from __future__ import annotations
from typing import Any
from copy import deepcopy

def apply_policy_overrides(live_policy_bundle: dict[str,Any], overrides: dict[str,Any]) -> dict[str,Any]:
    bundle = deepcopy(live_policy_bundle)
    for code, status in overrides.get("playbook_status_overrides",{}).items():
        bundle.setdefault("playbook_policy_registry",{}).setdefault(code,{})["status"] = status
    for status, patch in overrides.get("status_policy_overrides",{}).items():
        bundle.setdefault("playbook_capital_policy",{}).setdefault(status,{}).update(patch)
    for sym, val in overrides.get("symbol_concurrency_overrides",{}).items():
        bundle.setdefault("symbol_concurrency_overrides",{})[sym] = val
    for key, patch in overrides.get("execution_policy_overrides",{}).items():
        bundle.setdefault("execution_policy_overrides",{})[key] = patch
    if "surface_threshold_override" in overrides:
        bundle["surface_threshold_override"] = overrides["surface_threshold_override"]
    return bundle
