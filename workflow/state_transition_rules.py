"""workflow/state_transition_rules.py — Legal next-states for each object type and state."""
STATE_TRANSITION_RULES: dict = {
    "TRANSITION_CANDIDATE": {
        "DISCOVERED":{"APPROVED","BLOCKED","EXPIRED","CANCELLED"},
        "APPROVED":  {"QUEUED","DELAYED","BLOCKED","CANCELLED"},
        "QUEUED":    {"EXECUTED","DELAYED","BLOCKED","CANCELLED"},
        "DELAYED":   {"QUEUED","BLOCKED","EXPIRED","CANCELLED"},
        "BLOCKED":   {"QUEUED","EXPIRED","CANCELLED"},
        "EXECUTED":  set(), "EXPIRED": set(), "CANCELLED": set(),
    },
    "EXECUTION_TICKET": {
        "DRAFT":              {"READY","CANCELLED"},
        "READY":              {"PARTIALLY_EXECUTED","EXECUTED","FAILED","CANCELLED"},
        "PARTIALLY_EXECUTED": {"EXECUTED","FAILED","CANCELLED"},
        "EXECUTED": set(), "FAILED": set(), "CANCELLED": set(),
    },
    "POLICY_CHANGE_REQUEST": {
        "DRAFT":     {"SUBMITTED","ARCHIVED"},
        "SUBMITTED": {"APPROVED","REJECTED","ARCHIVED"},
        "APPROVED":  {"SUPERSEDED","ARCHIVED"},
        "REJECTED":  {"ARCHIVED"}, "SUPERSEDED": {"ARCHIVED"}, "ARCHIVED": set(),
    },
    "POLICY_VERSION": {
        "DRAFT":      {"SIMULATED","ARCHIVED"},
        "SIMULATED":  {"APPROVED","ARCHIVED"},
        "APPROVED":   {"LIVE","ARCHIVED"},
        "LIVE":       {"ROLLED_BACK","ARCHIVED"},
        "ROLLED_BACK":{"LIVE","ARCHIVED"},
        "ARCHIVED": set(),
    },
    "TRANSITION_JOURNAL": {
        "PENDING_OUTCOME":{"EXECUTED","ARCHIVED"},
        "EXECUTED":       {"EVALUATED","ARCHIVED"},
        "EVALUATED":      {"ARCHIVED"},
        "ARCHIVED": set(),
    },
}
