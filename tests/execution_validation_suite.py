"""tests/execution_validation_suite.py — Timing/stagger/fill quality tests."""
from __future__ import annotations
from tests.assertion_helpers import assert_equal, assert_gte
from tests.fixture_factory import make_position_row
from execution.stagger_policy_engine import decide_stagger_policy
from execution.fill_quality_engine import evaluate_fill_quality

def _pass(t): return {"test":t,"status":"PASS"}

def run_execution_validation_suite() -> list[dict]:
    results=[]
    row = make_position_row(transition_timing_score=82.0,transition_queue_score=85.0,
                            transition_avg_path_score=75.0,transition_execution_surface_score=76.0,
                            transition_rebuild_class="KEEP_LONG",transition_liquidity_score=74.0,
                            bot_priority="P3")
    pol = decide_stagger_policy(row)
    assert_equal(pol["execution_policy"],"FULL_NOW","strong timing → FULL_NOW")
    results.append(_pass("full-now on strong timing"))

    row2 = make_position_row(transition_timing_score=40.0,transition_queue_score=60.0,
                             transition_execution_surface_score=50.0,bot_priority="P5")
    pol2 = decide_stagger_policy(row2)
    assert_equal(pol2["execution_policy"],"DELAY","weak timing/surface → DELAY")
    results.append(_pass("delay on weak timing"))

    fill = evaluate_fill_quality({"estimated_net_credit":1.20},{"actual_net_credit":1.10})
    assert_gte(fill["fill_score"],50.0,"modest slippage still scores >= 50")
    results.append(_pass("fill quality scoring"))

    fill_perfect = evaluate_fill_quality({"estimated_net_credit":1.20},{"actual_net_credit":1.25})
    assert_equal(fill_perfect["fill_score"],100.0,"fill above estimate = 100")
    results.append(_pass("fill above estimate scores 100"))

    return results
