"""workflow/object_state_helpers.py — Standardized state access and terminal checks."""
from __future__ import annotations

TERMINAL_STATES: dict = {
    "TRANSITION_CANDIDATE": {"EXECUTED","EXPIRED","CANCELLED"},
    "EXECUTION_TICKET":     {"EXECUTED","FAILED","CANCELLED"},
    "POLICY_CHANGE_REQUEST":{"ARCHIVED"},
    "POLICY_VERSION":       {"ARCHIVED"},
    "TRANSITION_JOURNAL":   {"ARCHIVED"},
}

def get_state(obj: dict, default: str="UNKNOWN") -> str:
    return str(obj.get("state") or obj.get("status") or default)

def is_terminal_state(object_type: str, state: str) -> bool:
    return state in TERMINAL_STATES.get(object_type, set())

def get_allowed_transitions(object_type: str, current_state: str) -> set[str]:
    from workflow.state_transition_rules import STATE_TRANSITION_RULES
    return STATE_TRANSITION_RULES.get(object_type,{}).get(current_state, set())
