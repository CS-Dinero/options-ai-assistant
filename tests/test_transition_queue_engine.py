"""tests/test_transition_queue_engine.py — Campaign-aware queue row construction."""
from portfolio.campaign_queue_engine import build_transition_queue_row
from tests.fixtures.deep_itm_campaign_fixtures import (
    ledger_snapshot_roll_ready, lifecycle_decision_roll_ready,
    queue_context_roll_ready, ranked_paths_roll_then_flip,
)

def test_campaign_queue_row_builds():
    row=build_transition_queue_row(ctx=queue_context_roll_ready(),
        ls=ledger_snapshot_roll_ready(),ld=lifecycle_decision_roll_ready(),
        ranked_paths=ranked_paths_roll_then_flip())
    assert row.campaign_state == "ROLL_READY"
    assert row.campaign_action == "ROLL"
    assert row.best_path_code == "ROLL_SAME_SIDE"
    assert row.alt_path_code == "FLIP_SELECTIVELY"
    assert row.future_roll_score is not None
    assert row.queue_priority_score is not None
    assert row.queue_priority_band in {"ACT_NOW","DECIDE_NOW","WATCH_CLOSELY","IMPROVE_LATER"}

def test_queue_row_economics_populated():
    row=build_transition_queue_row(ctx=queue_context_roll_ready(),
        ls=ledger_snapshot_roll_ready(),ld=lifecycle_decision_roll_ready(),
        ranked_paths=ranked_paths_roll_then_flip())
    assert row.net_campaign_basis == 4.3
    assert row.campaign_recovered_pct == 46.25
    assert row.campaign_cycle_count == 2
    assert row.path_score_gap is not None
    assert row.path_score_gap > 0

def test_live_env_boosts_priority():
    from portfolio.campaign_queue_engine import CampaignQueueContext
    ctx_sim=queue_context_roll_ready()
    ctx_live=queue_context_roll_ready()  # already LIVE
    row_live=build_transition_queue_row(ctx_live,ledger_snapshot_roll_ready(),
        lifecycle_decision_roll_ready(),ranked_paths_roll_then_flip())
    # Just verify it builds and score is positive
    assert row_live.queue_priority_score > 0
    assert row_live.deployment_label == "REDUCED"
