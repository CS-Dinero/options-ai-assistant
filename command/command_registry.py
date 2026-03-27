"""command/command_registry.py — Executive dashboard module definitions."""
COMMAND_REGISTRY: dict = {
    "RISK_POSTURE":          {"description":"Top-level capital and risk posture."},
    "LIVE_CONTROL_STATE":    {"description":"Current mandate, live policy, environment, and release state."},
    "TOP_OPPORTUNITIES":     {"description":"Highest-priority actionable opportunities."},
    "TOP_BLOCKERS":          {"description":"Main constraints preventing action."},
    "REVIEW_PRESSURE":       {"description":"Human review load and urgent decisions."},
    "RELEASE_PRESSURE":      {"description":"Release bundles and rollout pressure."},
    "CAPITAL_DEPLOYMENT":    {"description":"Deployable capital and active envelope posture."},
    "MATURITY_POSTURE":      {"description":"How trustworthy major subsystems currently are."},
    "MOST_IMPORTANT_LEARNING":{"description":"Top causal / attribution / twin insight."},
}
