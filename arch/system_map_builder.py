"""arch/system_map_builder.py — Builds the unified living system map."""
from __future__ import annotations
from typing import Any
from arch.system_registry import SYSTEM_REGISTRY
from arch.component_catalog import COMPONENT_CATALOG
from arch.dependency_engine import DEPENDENCY_MAP
from arch.dataflow_engine import DATAFLOW_MAP
from arch.decisionflow_engine import DECISION_FLOW
from arch.policyflow_engine import POLICY_FLOW

def build_system_map(active_pruning_recommendations: list[dict[str,Any]]|None=None) -> dict[str,Any]:
    prune_state={r.get("component_id"):{"recommendation":r.get("recommendation"),"state":r.get("state")}
                 for r in (active_pruning_recommendations or []) if r.get("component_id")}
    components={cid:{**meta,"dependencies":DEPENDENCY_MAP.get(cid,[]),"pruning_state":prune_state.get(cid)}
                for cid,meta in COMPONENT_CATALOG.items()}
    return {"layers":SYSTEM_REGISTRY,"components":components,"dataflows":DATAFLOW_MAP,
            "decision_flow":DECISION_FLOW,"policy_flow":POLICY_FLOW}
