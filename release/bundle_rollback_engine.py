"""release/bundle_rollback_engine.py — Defines rollback triggers and reverse actions."""
from __future__ import annotations
from typing import Any

def build_bundle_rollback_plan(bundle_type: str) -> dict[str,Any]:
    conditions=["critical alerts rise materially after activation",
                "queue depth collapses below acceptable level",
                "blocked candidate rate spikes abnormally"]
    if bundle_type=="EXECUTION_HARDENING_BUNDLE":
        conditions.append("fill quality fails to improve or worsens materially")
    return {"rollback_conditions":conditions,"rollback_action":"restore prior approved policy / mandate / component state"}
