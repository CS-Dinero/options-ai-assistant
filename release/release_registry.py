"""release/release_registry.py — Release bundle type definitions."""
RELEASE_REGISTRY: dict = {
    "MANDATE_TUNING_BUNDLE":          {"description":"Grouped changes to mandate weights, overlays, or mandate-related behavior."},
    "PLAYBOOK_STATUS_BUNDLE":         {"description":"Grouped playbook promotion, demotion, or selective-use changes."},
    "REVIEW_SIMPLIFICATION_BUNDLE":   {"description":"Grouped review/handoff/workflow simplifications."},
    "EXECUTION_HARDENING_BUNDLE":     {"description":"Grouped changes to stagger rules, execution thresholds, or caution policies."},
    "QUEUE_HEALTH_BUNDLE":            {"description":"Grouped changes to improve queue depth, reduce starvation, or rebalance gating."},
    "CAPITAL_POLICY_BUNDLE":          {"description":"Grouped changes to sizing, concurrency, and capital commitment behavior."},
    "POLICY_STABILITY_BUNDLE":        {"description":"Grouped changes intended to reduce churn and improve operational stability."},
    "STRUCTURAL_SIMPLIFICATION_BUNDLE":{"description":"Grouped pruning, merge, or retirement changes to reduce framework complexity."},
}
