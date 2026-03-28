"""tests/test_campaign_basis_ledger.py — Ledger math correctness."""
from campaigns.campaign_basis_ledger import (
    initialize_campaign_ledger, apply_opening_entry, apply_harvest_credit,
    apply_roll_event, apply_repair_debit, build_campaign_ledger_snapshot,
)

def test_opening_debit_only():
    ledger=initialize_campaign_ledger("cmp_001","DEEP_ITM_CAMPAIGN","DEEP_ITM_CALENDAR_ENTRY",
        "2026-04-01T09:30:00","DEEP_ITM_CALENDAR","PUT")
    ledger=apply_opening_entry(ledger,"open_001","2026-04-01T09:30:00",8.0,0.0,"DEEP_ITM_CALENDAR","PUT")
    s=build_campaign_ledger_snapshot(ledger)
    assert s.net_campaign_basis == 8.0
    assert s.campaign_recovered_pct == 0.0
    assert s.campaign_realized_pnl == -8.0
    assert s.campaign_cycle_count == 0

def test_harvest_and_roll_math():
    ledger=initialize_campaign_ledger("cmp_001","DEEP_ITM_CAMPAIGN","DEEP_ITM_CALENDAR_ENTRY",
        "2026-04-01T09:30:00","DEEP_ITM_CALENDAR","PUT")
    ledger=apply_opening_entry(ledger,"open_001","2026-04-01T09:30:00",8.0,0.0,"DEEP_ITM_CALENDAR","PUT")
    ledger=apply_harvest_credit(ledger,"harvest_001","2026-04-04T15:30:00",2.5)
    s=build_campaign_ledger_snapshot(ledger)
    assert s.net_campaign_basis == 5.5
    assert s.campaign_recovered_pct == 31.25
    assert s.campaign_cycle_count == 1
    ledger=apply_roll_event(ledger,"roll_001","2026-04-05T10:15:00",1.0,2.2,
        "DEEP_ITM_CALENDAR","DEEP_ITM_DIAGONAL","PUT","PUT")
    s=build_campaign_ledger_snapshot(ledger)
    assert s.net_campaign_basis == 4.3
    assert s.campaign_recovered_pct == 46.25
    assert s.campaign_cycle_count == 2

def test_repair_debit_math():
    ledger=initialize_campaign_ledger("cmp_001","DEEP_ITM_CAMPAIGN","DEEP_ITM_CALENDAR_ENTRY","2026-04-01T09:30:00")
    ledger=apply_opening_entry(ledger,"open_001","2026-04-01T09:30:00",8.0,0.0,"DEEP_ITM_CALENDAR","PUT")
    ledger=apply_harvest_credit(ledger,"harvest_001","2026-04-04T15:30:00",2.5)
    ledger=apply_roll_event(ledger,"roll_001","2026-04-05T10:15:00",1.0,2.2,
        "DEEP_ITM_CALENDAR","DEEP_ITM_DIAGONAL","PUT","PUT")
    ledger=apply_repair_debit(ledger,"repair_001","2026-04-06T11:00:00",0.35)
    s=build_campaign_ledger_snapshot(ledger)
    assert s.net_campaign_basis == 4.65
    assert round(s.campaign_recovered_pct,3) == 41.875
