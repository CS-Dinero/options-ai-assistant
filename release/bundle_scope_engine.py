"""release/bundle_scope_engine.py — Calculates impacted components, layers, and flows."""
from __future__ import annotations
from typing import Any, Callable

def build_bundle_scope(included_changes: list[dict[str,Any]], impact_trace_fn: Callable) -> dict[str,Any]:
    impacted_components=set(); impacted_layers=set(); touches_core_flow=False
    for change in included_changes:
        cid=change.get("component_id"); layer=change.get("component_layer")
        if cid:
            impacted_components.add(cid)
            trace=impact_trace_fn(cid)
            for c in trace.get("downstream_impacted_components",[]): impacted_components.add(c)
        if layer: impacted_layers.add(layer)
        if change.get("core_flow",False): touches_core_flow=True
    return {"impacted_components":sorted(impacted_components),"impacted_layers":sorted(impacted_layers),
            "touches_core_flow":touches_core_flow}
