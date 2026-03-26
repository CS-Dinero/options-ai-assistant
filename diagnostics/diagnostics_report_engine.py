"""diagnostics/diagnostics_report_engine.py — Assembles all diagnostics into one package."""
from __future__ import annotations
from typing import Any
from diagnostics.block_reason_aggregator import aggregate_block_reasons
from diagnostics.gate_failure_engine import analyze_gate_failures
from diagnostics.queue_compression_engine import analyze_queue_compression
from diagnostics.policy_pressure_engine import analyze_policy_pressure
from diagnostics.slippage_hotspot_engine import find_slippage_hotspots
from diagnostics.playbook_drag_engine import analyze_playbook_drag

def build_diagnostics_report(rows: list[dict[str,Any]], queue: list[dict[str,Any]],
                               slippage_model: dict[str,Any],
                               playbook_stats: dict[str,Any]) -> dict[str,Any]:
    return {
        "block_reasons":   aggregate_block_reasons(rows),
        "gate_failures":   analyze_gate_failures(rows),
        "queue_compression": analyze_queue_compression(queue),
        "policy_pressure": analyze_policy_pressure(rows),
        "slippage_hotspots": find_slippage_hotspots(slippage_model),
        "playbook_drag":   analyze_playbook_drag(rows, playbook_stats),
    }
