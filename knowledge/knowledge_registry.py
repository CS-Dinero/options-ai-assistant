"""knowledge/knowledge_registry.py — Knowledge entry family definitions."""
KNOWLEDGE_REGISTRY: dict = {
    "SYMBOL_BEHAVIOR_NOTE":{"description":"Recurring behavior for a symbol under specific conditions."},
    "PLAYBOOK_CAVEAT":     {"description":"Context-specific caution or usage note for a playbook."},
    "EXECUTION_TRAP":      {"description":"Known execution condition that repeatedly harms fills."},
    "APPROVED_HEURISTIC":  {"description":"Human-approved operating heuristic."},
    "POLICY_RATIONALE":    {"description":"Why a policy was approved, activated, or rolled back."},
    "OVERRIDE_PATTERN":    {"description":"Repeated operator override indicating a model blind spot."},
    "QUEUE_PATTERN":       {"description":"Recurring queue or block-rate behavior worth remembering."},
    "CAPITAL_PATTERN":     {"description":"Recurring capital rotation or concurrency behavior."},
    "ROLLBACK_LESSON":     {"description":"What was learned from a rollback or rollback-watch episode."},
}
