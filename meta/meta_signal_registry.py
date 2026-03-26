"""meta/meta_signal_registry.py — Improvement signal families."""
META_SIGNAL_REGISTRY: dict = {
    "PLAYBOOK_DEGRADATION_SIGNAL":    {"description":"Evidence suggests a playbook is underperforming."},
    "PLAYBOOK_PROMOTION_SIGNAL":      {"description":"Evidence suggests a playbook is outperforming."},
    "SYMBOL_EXECUTION_FRICTION_SIGNAL":{"description":"Execution quality persistently weak for a symbol."},
    "QUEUE_STARVATION_SIGNAL":        {"description":"Queue quality suppressed; gate/threshold review needed."},
    "CAPITAL_CHOKE_SIGNAL":           {"description":"Capital/concurrency policy may be too restrictive."},
    "OVERRIDE_CONSENSUS_SIGNAL":      {"description":"Human overrides cluster around a repeated system weakness."},
    "POLICY_OVERRESTRICTION_SIGNAL":  {"description":"Policy appears too strict relative to evidence."},
    "POLICY_UNDERRESTRICTION_SIGNAL": {"description":"Policy appears too loose relative to outcomes."},
    "TIMING_POLICY_SIGNAL":           {"description":"Timing or stagger logic likely needs refinement."},
    "SURFACE_THRESHOLD_SIGNAL":       {"description":"Surface gating threshold likely needs refinement."},
}
