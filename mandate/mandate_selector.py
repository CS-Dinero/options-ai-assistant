"""mandate/mandate_selector.py — Chooses the active mandate from environment state."""
from __future__ import annotations
from typing import Any
from mandate.mandate_registry import DEFAULT_MANDATE

def select_active_mandate(environment_state: dict[str,Any], default_mandate: str=DEFAULT_MANDATE) -> str:
    return str(environment_state.get("active_mandate", default_mandate))
