"""playbooks/playbook_matcher.py — Maps row to playbook dict."""
from __future__ import annotations
from typing import Any
from playbooks.playbook_registry import PLAYBOOKS
from playbooks.playbook_rules import match_playbook_code

def build_playbook_match(row: dict[str,Any]) -> dict[str,Any]:
    code = match_playbook_code(row)
    meta = PLAYBOOKS.get(code,{"name":"Unknown Playbook","family":"UNKNOWN","default_status":"WATCHLIST"})
    return {"playbook_code":code,"playbook_name":meta["name"],
            "playbook_family":meta["family"],"playbook_status":meta.get("default_status","WATCHLIST")}
