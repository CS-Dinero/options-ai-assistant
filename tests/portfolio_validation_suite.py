"""tests/portfolio_validation_suite.py — Queue ordering and capital rotation tests."""
from __future__ import annotations
from tests.assertion_helpers import assert_equal, assert_true, assert_lte
from tests.fixture_factory import make_position_row
from portfolio.transition_queue_engine import build_transition_queue
from portfolio.capital_rotation_engine import evaluate_capital_rotation

def _pass(t): return {"test":t,"status":"PASS"}

def run_portfolio_validation_suite() -> list[dict]:
    results=[]
    r1 = make_position_row(id="pos_1",trade_id="pos_1",symbol="SPY",transition_queue_score=82.0,
                           transition_is_credit_approved=True,transition_improves_campaign=True,
                           transition_path_robust=True,transition_portfolio_fit_ok=True,
                           playbook_queue_bias=0.0,capital_commitment_decision="ALLOW_NORMAL")
    r2 = make_position_row(id="pos_2",trade_id="pos_2",symbol="QQQ",transition_queue_score=68.0,
                           transition_is_credit_approved=True,transition_improves_campaign=True,
                           transition_path_robust=True,transition_portfolio_fit_ok=True,
                           playbook_queue_bias=0.0,capital_commitment_decision="ALLOW_NORMAL")
    queue = build_transition_queue([r1,r2])
    assert_true(len(queue)>0, "queue not empty")
    if len(queue)>=2:
        assert_true(queue[0]["queue_score"]>=queue[1]["queue_score"], "queue sorted descending")
    results.append(_pass("queue ordering"))

    # PROMOTED playbook → ALLOW_FULL
    rot = evaluate_capital_rotation([],make_position_row(playbook_status="PROMOTED",
                                                          recommended_contract_add=2))
    assert_equal(rot["capital_commitment_decision"],"ALLOW_FULL","PROMOTED → ALLOW_FULL")
    results.append(_pass("capital rotation PROMOTED → ALLOW_FULL"))

    # DEMOTED playbook → smaller multiplier
    rot2 = evaluate_capital_rotation([],make_position_row(playbook_status="DEMOTED",
                                                           recommended_contract_add=2))
    assert_lte(rot2["size_multiplier"],0.50,"DEMOTED multiplier <= 0.50")
    results.append(_pass("capital rotation DEMOTED reduced multiplier"))

    return results
