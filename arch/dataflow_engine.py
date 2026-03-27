"""arch/dataflow_engine.py — Data movement between components and repositories."""
DATAFLOW_MAP: list = [
    {"source":"transition_journal_repository","target":"research_dataset_builder","data":"transition outcomes and journal rows"},
    {"source":"research_dataset_builder","target":"component_attribution_engine","data":"attribution-ready evidence rows"},
    {"source":"alert_rule_engine","target":"review_trigger_engine","data":"alerts requiring human review"},
    {"source":"path_ranker","target":"path_workspace_builder","data":"selected path and alternatives"},
    {"source":"path_workspace_builder","target":"transition_ticket_builder","data":"workspace-selected path and readiness context"},
    {"source":"decision_journal_repository","target":"override_analysis_engine","data":"human decisions and rationale"},
    {"source":"component_attribution_engine","target":"pruning_candidate_engine","data":"ROI and friction evidence"},
    {"source":"mandate_weight_engine","target":"transition_queue_engine","data":"mandate-adjusted scoring weights"},
    {"source":"rollback_watch_engine","target":"review_trigger_engine","data":"rollback-watch alerts"},
]
