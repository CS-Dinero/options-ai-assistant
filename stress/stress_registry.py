"""stress/stress_registry.py — Supported stress scenario families."""
STRESS_REGISTRY: dict = {
    "FILL_QUALITY_SHOCK":        {"description":"Reduce fill quality and worsen slippage conditions."},
    "QUEUE_STARVATION_SHOCK":    {"description":"Increase block rates and reduce queue depth."},
    "SYMBOL_CONCENTRATION_SHOCK":{"description":"Increase concentration pressure in one symbol."},
    "SURFACE_COMPRESSION_SHOCK": {"description":"Reduce execution-surface richness and raise block likelihood."},
    "CAPITAL_CHOKE_SHOCK":       {"description":"Increase capital block rate and concurrency pressure."},
    "PROMOTED_PLAYBOOK_DRIFT_SHOCK":{"description":"Degrade evidence quality in promoted playbooks."},
    "TIMING_FRICTION_SHOCK":     {"description":"Reduce timing quality and increase delay/stagger pressure."},
    "MANDATE_SWITCH_STRESS":     {"description":"Evaluate system behavior under a different active mandate."},
    "POLICY_TIGHTENING_STRESS":  {"description":"Test stricter policy thresholds and execution rules."},
    "COMBINED_RISK_STRESS":      {"description":"Apply multiple shocks at once to test resilience."},
}
