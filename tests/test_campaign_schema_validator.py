"""tests/test_campaign_schema_validator.py — Schema validator edge cases."""
from common.campaign_schema_validator import (
    validate_scanner_candidate, validate_enriched_row, validate_ledger_snapshot,
    validate_lifecycle_decision, validate_ranked_path, validate_queue_row,
    validate_workspace, validate_ticket, validate_trade_summary,
    validate_research_row, validate_journal_row, validate_campaign_pipeline_stage,
)
from tests.fixtures.deep_itm_campaign_fixtures import (
    ledger_snapshot_roll_ready, lifecycle_decision_roll_ready,
    ranked_paths_roll_then_flip, queue_context_roll_ready, ticket_input_roll_ready,
)

def test_valid_scanner_candidate():
    ok,errors=validate_scanner_candidate({"campaign_family":"DEEP_ITM_CAMPAIGN",
        "entry_family":"DEEP_ITM_CALENDAR_ENTRY","structure":"DEEP_ITM_CALENDAR",
        "entry_net_debit":7.5,"entry_cheapness_score":75.0,"future_roll_score":72.0,
        "candidate_score":76.0,"expected_move_clearance":0.42,"liquidity_score":80.0})
    assert ok

def test_invalid_campaign_family():
    ok,errors=validate_scanner_candidate({"campaign_family":"UNKNOWN","entry_family":"DEEP_ITM_CALENDAR_ENTRY",
        "structure":"X","entry_net_debit":7.5,"entry_cheapness_score":75.0,"future_roll_score":72.0,
        "candidate_score":76.0,"expected_move_clearance":0.42,"liquidity_score":80.0})
    assert not ok and any("campaign_family" in e for e in errors)

def test_valid_ledger_snapshot():
    ok,errors=validate_ledger_snapshot(ledger_snapshot_roll_ready())
    assert ok,f"Errors: {errors}"

def test_ledger_basis_formula_mismatch():
    import dataclasses
    bad=dataclasses.replace(ledger_snapshot_roll_ready(),net_campaign_basis=99.0)
    ok,errors=validate_ledger_snapshot(bad)
    assert not ok and any("mismatch" in e for e in errors)

def test_valid_lifecycle_decision():
    ok,errors=validate_lifecycle_decision(lifecycle_decision_roll_ready())
    assert ok,f"Errors: {errors}"

def test_invalid_campaign_state():
    import dataclasses
    bad=dataclasses.replace(lifecycle_decision_roll_ready(),campaign_state="PANIC_MODE")
    ok,errors=validate_lifecycle_decision(bad)
    assert not ok and any("campaign_state" in e for e in errors)

def test_valid_ranked_paths():
    for rp in ranked_paths_roll_then_flip():
        ok,errors=validate_ranked_path(rp); assert ok,f"Errors: {errors}"

def test_valid_queue_row():
    from portfolio.campaign_queue_engine import build_transition_queue_row
    qrow=build_transition_queue_row(ctx=queue_context_roll_ready(),
        ls=ledger_snapshot_roll_ready(),ld=lifecycle_decision_roll_ready(),
        ranked_paths=ranked_paths_roll_then_flip())
    ok,errors=validate_queue_row(qrow); assert ok,f"Errors: {errors}"

def test_dispatch_works():
    ok,errors=validate_campaign_pipeline_stage("ledger_snapshot",ledger_snapshot_roll_ready())
    assert ok,f"Errors: {errors}"

def test_dispatch_unknown_stage():
    ok,errors=validate_campaign_pipeline_stage("banana",{})
    assert not ok and "Unknown stage" in errors[0]
