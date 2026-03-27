"""arch/dependency_engine.py — Hard dependency map between components."""
DEPENDENCY_MAP: dict = {
    "transition_queue_engine":      ["capital_rotation_engine","mandate_weight_engine"],
    "narrative_engine":             ["transition_queue_engine","knowledge_linker"],
    "review_trigger_engine":        ["alert_rule_engine","diagnostics_report_engine"],
    "path_workspace_builder":       ["path_ranker","narrative_engine"],
    "refinement_candidate_engine":  ["override_analysis_engine","diagnostics_report_engine","playbook_rank_engine"],
    "policy_simulator":             ["transition_queue_engine","capital_rotation_engine","alert_rule_engine"],
    "stress_simulator":             ["policy_simulator","mandate_weight_engine","alert_rule_engine","rollback_watch_engine"],
    "pruning_candidate_engine":     ["component_attribution_engine"],
    "component_attribution_engine": ["transition_queue_engine"],
    "system_map_builder":           ["component_catalog","dependency_engine","dataflow_engine"],
}

def get_dependencies(component_id: str) -> list[str]:
    return DEPENDENCY_MAP.get(component_id, [])
