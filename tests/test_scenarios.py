"""tests/test_scenarios.py — Named validation scenarios."""
TEST_SCENARIOS: dict = {
    "HEALTHY_DIAGONAL":           {"description":"Approved same-side diagonal with solid scores."},
    "SURFACE_BLOCK":              {"description":"Transition blocked when surface falls below threshold."},
    "LIMITED_USE_HALF_SIZE":      {"description":"Limited-use playbook reduces final contract add."},
    "INVALID_WORKFLOW_JUMP":      {"description":"Workflow engine rejects illegal state change."},
    "ANALYST_CANNOT_APPROVE":     {"description":"Analyst role fails approval guard."},
    "POLICY_SIM_NON_MUTATING":    {"description":"Simulation must not change live policy bundle."},
    "ROLLBACK_RESTORES_LIVE":     {"description":"Rollback activates prior version correctly."},
    "DEMOTED_QUEUE_PENALTY":      {"description":"Demoted playbook lowers queue score."},
    "JOURNAL_LIFECYCLE":          {"description":"Journal moves PENDING→EXECUTED→EVALUATED correctly."},
    "CONCURRENCY_CAP":            {"description":"Concurrency engine blocks over-allocation."},
}
