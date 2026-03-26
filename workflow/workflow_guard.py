"""workflow/workflow_guard.py — Blocks invalid lifecycle transitions."""
from __future__ import annotations
from workflow.state_transition_rules import STATE_TRANSITION_RULES

class InvalidStateTransition(Exception):
    pass

def validate_transition(object_type: str, current_state: str, target_state: str) -> None:
    allowed = STATE_TRANSITION_RULES.get(object_type,{}).get(str(current_state) or "UNKNOWN", set())
    if target_state not in allowed:
        raise InvalidStateTransition(
            f"{object_type}: invalid {current_state} → {target_state} | allowed: {sorted(allowed)}")
