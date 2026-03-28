"""tests/test_campaign_workspace_builder.py — Campaign workspace panel completeness."""
from workspace.path_workspace_builder import build_campaign_path_execution_workspace
from tests.fixtures.deep_itm_campaign_fixtures import (
    ledger_snapshot_roll_ready, state_decision_roll_ready,
    ranked_paths_roll_then_flip, workspace_input_roll_ready,
)

def test_campaign_workspace_builds():
    ws=build_campaign_path_execution_workspace(wi=workspace_input_roll_ready(),
        ls=ledger_snapshot_roll_ready(),sd=state_decision_roll_ready(),
        ranked_paths=ranked_paths_roll_then_flip())
    # Economics panel
    assert ws.campaign_economics["opening_debit"] == 8.0
    assert ws.campaign_economics["net_campaign_basis"] == 4.3
    assert ws.campaign_economics["campaign_recovered_pct"] == 46.25
    # Paths
    assert ws.selected_path is not None
    assert ws.selected_path["path_code"] == "ROLL_SAME_SIDE"
    assert ws.alternative_path is not None
    assert ws.alternative_path["path_code"] == "FLIP_SELECTIVELY"
    # Roll panel
    assert ws.roll_panel["roll_credit_est"] == 0.70
    assert ws.roll_panel["future_roll_score"] == 80.0
    assert ws.roll_panel["proposed_short_strike"] == 240.0
    assert ws.roll_panel["expected_move_clearance"] == 0.95
    # Transition panel
    assert len(ws.transition_panel["transition_choices"]) >= 1
    assert ws.transition_panel["transition_choices"][0]["path_code"] == "ROLL_SAME_SIDE"
    assert ws.transition_panel["flip_candidate"] is not None

def test_workspace_execution_panel():
    ws=build_campaign_path_execution_workspace(wi=workspace_input_roll_ready(),
        ls=ledger_snapshot_roll_ready(),sd=state_decision_roll_ready(),
        ranked_paths=ranked_paths_roll_then_flip())
    ep=ws.execution_panel
    assert ep["campaign_action"] == "ROLL"
    assert ep["campaign_state"] == "ROLL_READY"
    assert ep["selected_path_code"] == "ROLL_SAME_SIDE"
    assert ep["selected_path_approved"] is True
