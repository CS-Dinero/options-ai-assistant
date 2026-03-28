"""tests/test_campaign_path_simulator.py — Multi-step simulation correctness."""
from simulation.campaign_path_simulator import (
    CampaignSimulationConfig, CampaignSimulationStepInput,
    simulate_campaign_path_v2 as simulate_campaign_path,
)
from tests.fixtures.deep_itm_campaign_fixtures import ranked_paths_roll_then_flip

def test_campaign_simulation_simple_path():
    ranked=ranked_paths_roll_then_flip()
    steps=[
        CampaignSimulationStepInput(step_index=1,timestamp_utc="2026-04-04T15:30:00",symbol="TSLA",
            current_structure="DEEP_ITM_CALENDAR",current_side="PUT",current_profit_percent=35.0,
            campaign_unrealized_pnl=1.0,execution_surface_score=82.0,timing_score=81.0,
            regime_alignment_score=85.0,distance_to_strike=12.0,expected_move=12.0,
            short_dte=6,long_dte=35,ranked_paths=ranked),
        CampaignSimulationStepInput(step_index=2,timestamp_utc="2026-04-08T14:00:00",symbol="TSLA",
            current_structure="DEEP_ITM_DIAGONAL",current_side="PUT",current_profit_percent=42.0,
            campaign_unrealized_pnl=0.8,execution_surface_score=80.0,timing_score=79.0,
            regime_alignment_score=85.0,distance_to_strike=14.0,expected_move=12.0,
            short_dte=5,long_dte=31,ranked_paths=ranked),
        CampaignSimulationStepInput(step_index=3,timestamp_utc="2026-04-10T15:45:00",symbol="TSLA",
            current_structure="DEEP_ITM_DIAGONAL",current_side="PUT",current_profit_percent=55.0,
            campaign_unrealized_pnl=0.5,execution_surface_score=78.0,timing_score=80.0,
            regime_alignment_score=84.0,distance_to_strike=16.0,expected_move=12.0,
            short_dte=4,long_dte=28,ranked_paths=[],close_cost=0.0),
    ]
    result=simulate_campaign_path(campaign_id="cmp_tsla_sim_001",symbol="TSLA",
        campaign_family="DEEP_ITM_CAMPAIGN",entry_family="DEEP_ITM_CALENDAR_ENTRY",
        opening_timestamp_utc="2026-04-01T09:30:00",opening_structure="DEEP_ITM_CALENDAR",
        opening_side="PUT",opening_debit=8.0,opening_credit=0.0,step_inputs=steps,
        cfg=CampaignSimulationConfig(max_cycles=12,max_steps=10))
    assert result.step_count >= 1
    assert result.final_ledger_snapshot.campaign_cycle_count >= 1
    assert result.final_ledger_snapshot.net_campaign_basis <= 8.0

def test_simulation_tracks_transition_history():
    ranked=ranked_paths_roll_then_flip()
    steps=[CampaignSimulationStepInput(step_index=1,timestamp_utc="2026-04-04T15:30:00",symbol="TSLA",
        current_structure="DEEP_ITM_CALENDAR",current_side="PUT",current_profit_percent=35.0,
        campaign_unrealized_pnl=1.0,execution_surface_score=82.0,timing_score=81.0,
        regime_alignment_score=85.0,distance_to_strike=12.0,expected_move=12.0,
        short_dte=6,long_dte=35,ranked_paths=ranked)]
    result=simulate_campaign_path("sim_002","TSLA","DEEP_ITM_CAMPAIGN","DEEP_ITM_CALENDAR_ENTRY",
        "2026-04-01T09:30:00","DEEP_ITM_CALENDAR","PUT",8.0,0.0,steps)
    assert isinstance(result.transition_history,list)
    assert len(result.transition_history) >= 1
    assert isinstance(result.final_pnl,float)
