"""tests/test_campaign_trade_logger.py — Trade logger event accumulation."""
from performance.trade_logger import (
    initialize_campaign_trade_record, log_open_entry, log_campaign_transition,
    build_campaign_trade_summary, campaign_trade_events_to_dicts,
)

def test_campaign_trade_logger_sequence():
    record=initialize_campaign_trade_record("cmp_tsla_001","TSLA","DEEP_ITM_CAMPAIGN",
        "DEEP_ITM_CALENDAR_ENTRY","2026-04-01T09:30:00","DEEP_ITM_CALENDAR","PUT","NEUTRAL_TIME_SPREADS")
    record=log_open_entry(record,"open_001",8.0,regime_at_decision="NEUTRAL_TIME_SPREADS")
    record=log_campaign_transition(record,"harvest_001","HARVEST","HARVEST",2.5,0.0,
        net_campaign_basis=5.5,campaign_recovered_pct=31.25,campaign_cycle_count=1,current_profit_percent=35.0)
    record=log_campaign_transition(record,"roll_001","ROLL_SAME_SIDE","ROLL_SAME_SIDE",2.2,1.0,
        net_campaign_basis=4.3,campaign_recovered_pct=46.25,campaign_cycle_count=2,current_profit_percent=42.0,
        future_roll_score_at_decision=76.0)
    summary=build_campaign_trade_summary(record)
    assert summary["opening_debit"] == 8.0
    assert summary["realized_credit_collected"] == 4.7
    assert summary["realized_close_cost"] == 1.0
    assert summary["net_campaign_basis"] == 4.3
    assert summary["campaign_cycle_count"] == 2
    assert summary["event_count"] == 3

def test_trade_events_list():
    record=initialize_campaign_trade_record("cmp_001","TSLA","DEEP_ITM_CAMPAIGN","DEEP_ITM_CALENDAR_ENTRY")
    record=log_open_entry(record,"e1",5.00)
    record=log_campaign_transition(record,"e2","HARVEST","HARVEST",2.00,0.0)
    events=campaign_trade_events_to_dicts(record)
    assert len(events) == 2
    assert events[0]["event_type"] == "OPEN_ENTRY"
    assert events[1]["event_type"] == "HARVEST"
    assert events[1]["realized_credit"] == 2.00

def test_max_profit_tracking():
    record=initialize_campaign_trade_record("cmp_001","TSLA","DEEP_ITM_CAMPAIGN","DEEP_ITM_CALENDAR_ENTRY")
    record=log_open_entry(record,"e1",8.00)
    record=log_campaign_transition(record,"e2","HARVEST","HARVEST",2.5,0.0,current_profit_percent=35.0)
    record=log_campaign_transition(record,"e3","ROLL_SAME_SIDE","ROLL_SAME_SIDE",2.2,1.0,current_profit_percent=48.0)
    record=log_campaign_transition(record,"e4","ROLL_SAME_SIDE","ROLL_SAME_SIDE",1.8,0.8,current_profit_percent=40.0)
    s=build_campaign_trade_summary(record)
    assert s["max_profit_percent_seen"] == 48.0
