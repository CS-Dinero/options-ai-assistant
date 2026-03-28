"""tests/test_campaign_path_ranker.py — Path ranking mandate-alignment checks."""
from compare.campaign_path_ranker import PathRankingContext, rank_campaign_paths
from campaigns.campaign_transition_engine import build_transition_candidates, CampaignTransitionContext
from tests.fixtures.deep_itm_campaign_fixtures import (
    ranked_paths_roll_then_flip, ledger_snapshot_roll_ready, lifecycle_decision_roll_ready,
)

def test_roll_outranks_flip_fixture():
    ranked=ranked_paths_roll_then_flip()
    assert ranked[0].path_code == "ROLL_SAME_SIDE"
    assert ranked[0].path_total_score > ranked[1].path_total_score
    assert ranked[0].approved is True
    assert ranked[1].approved is False

def test_basis_recovery_mandate_promotes_roll():
    snap=ledger_snapshot_roll_ready(); ld=lifecycle_decision_roll_ready()
    from campaigns.campaign_transition_engine import TransitionCandidate
    roll=TransitionCandidate("ROLL_SAME_SIDE","TSLA","cmp_tsla_001","DEEP_ITM_CAMPAIGN",
        "DEEP_ITM_CALENDAR_ENTRY","CALENDAR","CALENDAR","PUT","PUT",0.70,0.0,3.60,
        72.0,80.0,0.0,0.0,62.0,82.0,85.0,75.0,True,"Approved.",{})
    flip=TransitionCandidate("FLIP_SELECTIVELY","TSLA","cmp_tsla_001","DEEP_ITM_CAMPAIGN",
        "DEEP_ITM_CALENDAR_ENTRY","CALENDAR","CALENDAR","PUT","CALL",0.85,0.0,3.45,
        68.0,62.0,76.0,0.0,62.0,75.0,78.0,55.0,False,"Same-side stronger.",{"flip_to_side":"CALL"})
    ctx=PathRankingContext("TSLA","BASIS_RECOVERY",snap.campaign_recovered_pct,snap.net_campaign_basis,
        82.0,81.0,85.0,62.0,42.0)
    ranked=rank_campaign_paths([roll,flip],ctx)
    assert ranked[0].path_code == "ROLL_SAME_SIDE", f"top={ranked[0].path_code}"
    assert ranked[0].path_total_score > ranked[1].path_total_score
