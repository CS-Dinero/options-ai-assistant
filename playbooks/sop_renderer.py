"""playbooks/sop_renderer.py — Renders transition-specific SOP from template."""
from __future__ import annotations
from typing import Any
from playbooks.sop_templates import SOP_TEMPLATES

def _sf(v,d=0.0):
    try: return float(v) if v not in(None,"","—") else d
    except: return d

def render_playbook_sop(row: dict[str,Any]) -> dict[str,Any]:
    code   = str(row.get("playbook_code","PB001"))
    tmpl   = SOP_TEMPLATES.get(code,{"setup":[],"execution":[],"invalidation":[],"next_step":[]})
    sym    = str(row.get("symbol","?"))
    action = str(row.get("transition_action","?")).replace("_"," ").title()
    credit = _sf(row.get("transition_net_credit"))
    policy = str(row.get("transition_execution_policy","DELAY"))
    ex_steps = list(tmpl.get("execution",[]))
    ex_steps.insert(0,f"{sym}: execute {action} only if expected credit remains near ${credit:.2f}/share.")
    ex_steps.append(f"Execution policy: {policy}.")
    return {"sop_setup":tmpl.get("setup",[]),"sop_execution":ex_steps,
            "sop_invalidation":tmpl.get("invalidation",[]),"sop_next_step":tmpl.get("next_step",[])}
