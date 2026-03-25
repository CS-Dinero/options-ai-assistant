"""playbooks/playbook_audit_tags.py — Structured review tags for research linkage."""
from __future__ import annotations

def build_playbook_audit_tags(row: dict) -> list[str]:
    tags=[]
    code=row.get("playbook_code"); family=row.get("playbook_family")
    rb=row.get("transition_rebuild_class"); action=row.get("transition_action")
    status=row.get("playbook_status","WATCHLIST")
    if code:   tags.append(code)
    if family: tags.append(f"FAMILY:{family}")
    if rb:     tags.append(f"REBUILD:{rb}")
    if action: tags.append(f"ACTION:{action.replace('_','.')}")
    if status: tags.append(f"STATUS:{status}")
    pol=row.get("transition_execution_policy","")
    if pol=="FULL_NOW": tags.append("STATE:READY")
    elif pol=="STAGGER": tags.append("STATE:STAGGER")
    elif pol=="DELAY":   tags.append("STATE:DELAY")
    return tags
