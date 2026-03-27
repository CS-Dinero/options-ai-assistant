"""risk/capital_decision_engine.py — Combines envelope + maturity + confidence + path → final sizing."""
from __future__ import annotations
from typing import Any

def build_capital_decision(base_contract_add: float, risk_envelope: dict[str,Any],
                            confidence_weight: float, maturity_weight: float, path_weight: float,
                            mandate_size_multiplier: float, playbook_size_multiplier: float,
                            exposure_eval: dict[str,Any], capital_budget: dict[str,Any]) -> dict[str,Any]:
    env_mult=float(risk_envelope.get("base_size_multiplier",1.0))
    available=float(capital_budget.get("available_incremental_risk",1.0))
    raw=env_mult*confidence_weight*maturity_weight*path_weight*mandate_size_multiplier*playbook_size_multiplier
    if not exposure_eval.get("exposure_within_limit",True): raw*=0.50
    final=max(0.0,float(base_contract_add)*raw)
    if available<=0:     label="NO_DEPLOY"; final=0.0
    elif final<=0.25:    label="TOKEN"
    elif final<=0.75:    label="REDUCED"
    elif final<=1.15:    label="NORMAL"
    else:                label="EXPANDED"
    return {"raw_capital_multiplier":round(raw,3),"final_contract_add":round(final,2),
            "capital_deployment_label":label}
