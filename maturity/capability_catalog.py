"""maturity/capability_catalog.py — Capabilities available for maturity scoring."""
CAPABILITY_CATALOG: dict = {
    "EXECUTION_ENGINE":        {"layer":"DECISION"},
    "TRANSITION_QUEUE":        {"layer":"DECISION"},
    "WORKSPACE":               {"layer":"EXECUTION_WORKFLOW"},
    "REVIEW_SYSTEM":           {"layer":"HUMAN_SUPERVISION"},
    "HANDOFF_SYSTEM":          {"layer":"HUMAN_SUPERVISION"},
    "POLICY_ENGINE":           {"layer":"GOVERNANCE"},
    "MANDATE_SYSTEM":          {"layer":"ADAPTATION"},
    "ATTRIBUTION_ENGINE":      {"layer":"ADAPTATION"},
    "PRUNING_ENGINE":          {"layer":"ADAPTATION"},
    "RELEASE_SYSTEM":          {"layer":"GOVERNANCE"},
    "KNOWLEDGE_BASE":          {"layer":"INTELLIGENCE"},
    "STRESS_TESTING":          {"layer":"ADAPTATION"},
    "COMPARATIVE_PATHS":       {"layer":"DECISION"},
    "DIGITAL_TWIN":            {"layer":"INTELLIGENCE"},
}
