"""tests/test_campaign_research_builder.py — Research row schema correctness."""
from research.campaign_research_builder import (
    build_research_row_from_queue_row, build_research_row_from_trade_record,
    build_research_row_from_lifecycle_decision, research_dataset_row_to_dict,
)
from portfolio.campaign_queue_engine import build_transition_queue_row
from performance.trade_logger import (
    initialize_campaign_trade_record, log_open_entry, log_campaign_transition,
)
from tests.fixtures.deep_itm_campaign_fixtures import (
    ledger_snapshot_roll_ready, lifecycle_decision_roll_ready,
    queue_context_roll_ready, ranked_paths_roll_then_flip,
)

def test_research_row_from_queue():
    qrow=build_transition_queue_row(ctx=queue_context_roll_ready(),
        ls=ledger_snapshot_roll_ready(),ld=lifecycle_decision_roll_ready(),
        ranked_paths=ranked_paths_roll_then_flip())
    rr=build_research_row_from_queue_row(qrow)
    assert rr.campaign_family == "DEEP_ITM_CAMPAIGN"
    assert rr.entry_family == "DEEP_ITM_CALENDAR_ENTRY"
    assert rr.transition_family == "ROLL_SAME_SIDE"
    assert rr.campaign_state == "ROLL_READY"
    assert rr.campaign_recovered_pct == 46.25
    assert rr.future_roll_score is not None
    assert rr.row_source == "QUEUE_ROW"

def test_research_row_from_trade_record():
    record=initialize_campaign_trade_record("cmp_tsla_001","TSLA","DEEP_ITM_CAMPAIGN","DEEP_ITM_CALENDAR_ENTRY")
    record=log_open_entry(record,"open_001",8.0)
    record=log_campaign_transition(record,"roll_001","ROLL_SAME_SIDE","ROLL_SAME_SIDE",2.2,1.0,
        net_campaign_basis=6.8,campaign_recovered_pct=15.0,campaign_cycle_count=1)
    rr=build_research_row_from_trade_record(record,"LIVE")
    assert rr.campaign_family == "DEEP_ITM_CAMPAIGN"
    assert rr.entry_family == "DEEP_ITM_CALENDAR_ENTRY"
    assert rr.row_source == "TRADE_RECORD"

def test_research_row_from_lifecycle_decision():
    rr=build_research_row_from_lifecycle_decision(lifecycle_decision_roll_ready(),
        ledger_snapshot_roll_ready(),"TSLA","LIVE","DEEP_ITM_CALENDAR","PUT","NORMAL","NORMAL","GOVERNED")
    assert rr.campaign_state == "ROLL_READY"
    assert rr.selected_transition_type == "ROLL_SAME_SIDE"
    assert rr.future_roll_score == 76.0
    assert rr.row_source == "LIFECYCLE_DECISION"

def test_research_row_to_dict():
    qrow=build_transition_queue_row(ctx=queue_context_roll_ready(),
        ls=ledger_snapshot_roll_ready(),ld=lifecycle_decision_roll_ready(),
        ranked_paths=ranked_paths_roll_then_flip())
    rr=build_research_row_from_queue_row(qrow)
    d=research_dataset_row_to_dict(rr)
    assert isinstance(d,dict)
    assert d["campaign_family"] == "DEEP_ITM_CAMPAIGN"
    assert d["row_source"] == "QUEUE_ROW"
    assert "path_recommended" in d and "path_selected" in d and "path_executed" in d
