"""meta/refinement_candidate_engine.py — Builds refinement candidates from evidence."""
from __future__ import annotations
from typing import Any

def build_refinement_candidates(
    diagnostics: dict[str,Any], playbook_stats: dict[str,Any], playbook_statuses: dict[str,Any],
    override_analysis: dict[str,Any], slippage_hotspots: dict[str,Any], metrics: dict[str,Any],
) -> list[dict[str,Any]]:
    candidates: list[dict[str,Any]]=[]

    worst_sym=slippage_hotspots.get("worst_symbol"); worst_win=slippage_hotspots.get("worst_window")
    if worst_sym:
        candidates.append({"signal_type":"SYMBOL_EXECUTION_FRICTION_SIGNAL","target_type":"SYMBOL",
            "target_id":worst_sym,"refinement_type":"TIGHTEN_EXECUTION_POLICY",
            "proposed_change":{"symbol":worst_sym,"window":worst_win,
                               "action":"increase execution caution / prefer stagger"},
            "evidence":slippage_hotspots})

    gate=diagnostics.get("gate_failures",{})
    if float(gate.get("surface_fail_pct",0.0))>=0.40:
        candidates.append({"signal_type":"SURFACE_THRESHOLD_SIGNAL","target_type":"THRESHOLD",
            "target_id":"surface_threshold","refinement_type":"REVIEW_SURFACE_THRESHOLD",
            "proposed_change":{"current_pressure":gate.get("surface_fail_pct"),
                               "action":"consider softening surface threshold by regime/symbol"},
            "evidence":gate})

    status_map=playbook_statuses.get("playbook_statuses",{}); by_pb=playbook_stats.get("by_playbook",{})
    for code,stats in by_pb.items():
        status=status_map.get(code,{}).get("status"); count=int(stats.get("count",0))
        outcome=float(stats.get("avg_outcome_score",0))
        if status=="PROMOTED" and count>=10 and outcome<65:
            candidates.append({"signal_type":"PLAYBOOK_DEGRADATION_SIGNAL","target_type":"PLAYBOOK",
                "target_id":code,"refinement_type":"REVIEW_PLAYBOOK_STATUS_DOWN",
                "proposed_change":{"playbook_code":code,"current_status":status,"suggested_status":"WATCHLIST"},
                "evidence":stats})
        if status in ("WATCHLIST","LIMITED_USE") and count>=10 and outcome>=75:
            candidates.append({"signal_type":"PLAYBOOK_PROMOTION_SIGNAL","target_type":"PLAYBOOK",
                "target_id":code,"refinement_type":"REVIEW_PLAYBOOK_STATUS_UP",
                "proposed_change":{"playbook_code":code,"current_status":status,"suggested_status":"PROMOTED"},
                "evidence":stats})

    oc=override_analysis.get("primary_reason_counts",{})
    if oc.get("SLIPPAGE_RISK_TOO_HIGH",0)>=3:
        candidates.append({"signal_type":"OVERRIDE_CONSENSUS_SIGNAL","target_type":"EXECUTION_POLICY",
            "target_id":"slippage_override_cluster","refinement_type":"REVIEW_STAGGER_RULES",
            "proposed_change":{"action":"prefer stagger for patterns frequently deferred due to slippage risk"},
            "evidence":override_analysis})

    if float(metrics.get("capital_block_rate",0.0))>=0.35:
        candidates.append({"signal_type":"CAPITAL_CHOKE_SIGNAL","target_type":"CAPITAL_POLICY",
            "target_id":"capital_block_rate","refinement_type":"REVIEW_CAPITAL_CONSTRAINTS",
            "proposed_change":{"action":"review concurrency or capital block settings"},
            "evidence":metrics})

    return candidates
