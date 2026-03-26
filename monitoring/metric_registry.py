"""monitoring/metric_registry.py — Operational metric definitions."""
METRIC_REGISTRY: dict = {
    "avg_fill_score_recent":        {"description":"Average recent execution fill score."},
    "avg_slippage_recent":          {"description":"Average recent slippage in dollars."},
    "blocked_candidate_rate":       {"description":"Fraction of rows blocked by one or more gates."},
    "surface_block_rate":           {"description":"Fraction blocked by execution surface."},
    "timing_block_rate":            {"description":"Fraction blocked by timing."},
    "queue_depth":                  {"description":"Number of queue-approved candidates."},
    "queue_compression_rate":       {"description":"Fraction of candidates outside top queue slice."},
    "top_symbol_concentration":     {"description":"Largest current symbol concentration."},
    "capital_block_rate":           {"description":"Fraction blocked by capital commitment."},
    "delay_rate":                   {"description":"Fraction of candidates marked DELAY."},
    "promoted_playbook_outcome_drift":{"description":"Outcome deterioration among promoted playbooks."},
}
