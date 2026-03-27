"""arch/decisionflow_engine.py — How recommendations become actions."""
DECISION_FLOW: list = [
    "transition_queue_engine","path_ranker","narrative_engine",
    "review_trigger_engine","review_resolution_engine","decision_packet_builder",
    "path_workspace_builder","transition_ticket_builder",
    "execution_engine","transition_journal_repository",
]
