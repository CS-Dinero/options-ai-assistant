"""history/snapshot_registry.py — Snapshot family definitions."""
SNAPSHOT_REGISTRY: dict = {
    "QUEUE_SNAPSHOT":      {"description":"Queue depth, score, ready/stagger/delay counts."},
    "PORTFOLIO_SNAPSHOT":  {"description":"Portfolio basis, posture, concentration, capital state."},
    "EXECUTION_SNAPSHOT":  {"description":"Fill quality, slippage, timing/surface metrics."},
    "PLAYBOOK_SNAPSHOT":   {"description":"Playbook status, outcome drift, drag, promotion state."},
    "ALERT_SNAPSHOT":      {"description":"Current alert counts and severities."},
    "POLICY_STATE_SNAPSHOT":{"description":"Live policy version, active biases, environment state."},
}
