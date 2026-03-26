"""monitoring/alert_rule_engine.py — Evaluates metrics against thresholds and emits alerts."""
from __future__ import annotations
from typing import Any
from datetime import datetime
import uuid

def _eval(metric_name, value, rules):
    if "critical_above" in rules and value>=rules["critical_above"]: return "CRITICAL"
    if "warning_above"  in rules and value>=rules["warning_above"]:  return "WARNING"
    if "critical_below" in rules and value<=rules["critical_below"]: return "CRITICAL"
    if "warning_below"  in rules and value<=rules["warning_below"]:  return "WARNING"
    return None

def build_alerts(metrics: dict[str,Any], threshold_registry: dict[str,Any],
                 environment: str="LIVE") -> list[dict[str,Any]]:
    alerts=[]
    for metric_name,value in metrics.items():
        rules=threshold_registry.get(metric_name)
        if not rules: continue
        severity=_eval(metric_name, float(value), rules)
        if severity:
            alerts.append({"alert_id":str(uuid.uuid4()),"timestamp_utc":datetime.utcnow().isoformat(),
                           "metric_name":metric_name,"metric_value":value,"severity":severity,
                           "environment":environment,
                           "summary":f"{metric_name} triggered {severity} at {value}"})
    return alerts
