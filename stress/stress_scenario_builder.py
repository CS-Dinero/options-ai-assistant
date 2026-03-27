"""stress/stress_scenario_builder.py — Combines shocks into named scenario packages."""
from __future__ import annotations
from typing import Any

def build_stress_scenario(scenario_name: str, active_mandate: str, shocks: list[dict[str,Any]],
                           mandate_override: str|None=None, policy_override: dict[str,Any]|None=None) -> dict[str,Any]:
    return {"scenario_name":scenario_name,"baseline_mandate":active_mandate,
            "effective_mandate":mandate_override or active_mandate,
            "shocks":shocks,"policy_override":policy_override or {}}
