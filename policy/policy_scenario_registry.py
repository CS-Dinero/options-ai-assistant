"""policy/policy_scenario_registry.py — Named what-if policy scenarios."""
from __future__ import annotations

POLICY_SCENARIOS: dict = {
    "DEMOTE_PB002":       {"name":"Demote PB002","overrides":{"playbook_status_overrides":{"PB002":"DEMOTED"}}},
    "TSLA_ONE_SLOT":      {"name":"TSLA max concurrency = 1","overrides":{"symbol_concurrency_overrides":{"TSLA":1}}},
    "LIMITED_HALF_SIZE":  {"name":"Limited-use playbooks half-size",
                           "overrides":{"status_policy_overrides":{"LIMITED_USE":{"size_multiplier":0.50}}}},
    "REPLACE_LONG_STAGGER":{"name":"Force stagger for replace-long diagonals",
                            "overrides":{"execution_policy_overrides":{"REPLACE_LONG":{"force_policy":"STAGGER"}}}},
    "TIGHTER_SURFACE":    {"name":"Raise surface threshold to 72","overrides":{"surface_threshold_override":72.0}},
}
