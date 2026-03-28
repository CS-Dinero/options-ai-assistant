"""tests/test_campaign_journal.py — Journal lifecycle correctness."""
from journal.campaign_transition_journal import (
    build_transition_journal_row, mark_transition_executed,
    mark_transition_deferred, mark_transition_closed, transition_journal_row_to_dict,
)
from tests.fixtures.deep_itm_campaign_fixtures import (
    ledger_snapshot_roll_ready, lifecycle_decision_roll_ready, ranked_paths_roll_then_flip,
)

def test_transition_journal_row_and_execute():
    row=build_transition_journal_row("jrnl_001","LIVE","TSLA","pos_001","cmp_tsla_001",
        "DEEP_ITM_CAMPAIGN","DEEP_ITM_CALENDAR_ENTRY","DEEP_ITM_CALENDAR","PUT",
        ledger_snapshot_roll_ready(),lifecycle_decision_roll_ready(),ranked_paths_roll_then_flip())
    assert row.path_recommended == "ROLL_SAME_SIDE"
    assert row.journal_status == "OPEN"
    assert row.best_path_code == "ROLL_SAME_SIDE"
    assert row.alt_path_code == "FLIP_SELECTIVELY"
    assert row.net_campaign_basis == 4.3
    assert row.future_roll_score == 80.0

    row2=mark_transition_executed(row,"ROLL_SAME_SIDE",["Executed same-side continuation roll."])
    assert row2.path_executed == "ROLL_SAME_SIDE"
    assert row2.journal_status == "EXECUTED"
    assert "Executed same-side" in " ".join(row2.notes)

def test_journal_defer_and_close():
    row=build_transition_journal_row("jrnl_002","LIVE","TSLA","pos_001","cmp_tsla_001",
        "DEEP_ITM_CAMPAIGN","DEEP_ITM_CALENDAR_ENTRY","DEEP_ITM_CALENDAR","PUT",
        ledger_snapshot_roll_ready(),lifecycle_decision_roll_ready(),ranked_paths_roll_then_flip())
    row2=mark_transition_deferred(row,"Surface too weak today.")
    assert row2.journal_status == "DEFERRED"
    row3=mark_transition_closed(row,"Campaign wound down successfully.")
    assert row3.journal_status == "CLOSED"

def test_journal_to_dict():
    row=build_transition_journal_row("jrnl_003","LIVE","TSLA","pos_001","cmp_tsla_001",
        "DEEP_ITM_CAMPAIGN","DEEP_ITM_CALENDAR_ENTRY","DEEP_ITM_CALENDAR","PUT",
        ledger_snapshot_roll_ready(),lifecycle_decision_roll_ready(),ranked_paths_roll_then_flip())
    row=mark_transition_executed(row,"ROLL_SAME_SIDE")
    d=transition_journal_row_to_dict(row)
    assert isinstance(d,dict)
    assert d["journal_status"] == "EXECUTED"
    assert d["path_executed"] == "ROLL_SAME_SIDE"
    assert d["path_recommended"] == "ROLL_SAME_SIDE"
    assert d["net_campaign_basis"] == 4.3
