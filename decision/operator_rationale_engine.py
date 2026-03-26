"""decision/operator_rationale_engine.py — Attaches structured rationale to a decision."""
from __future__ import annotations
from typing import Any

def attach_operator_rationale(decision_packet: dict[str,Any], agreement_mode: str, confidence: str,
                               primary_reason_code: str, secondary_reason_codes: list[str]|None=None,
                               freeform_note: str="", followup_required: bool=False) -> dict[str,Any]:
    out=dict(decision_packet)
    out["rationale"]={"agreement_mode":agreement_mode,"confidence":confidence,
                      "primary_reason_code":primary_reason_code,
                      "secondary_reason_codes":secondary_reason_codes or [],
                      "freeform_note":freeform_note,"followup_required":followup_required}
    return out
