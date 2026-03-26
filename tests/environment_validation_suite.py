"""tests/environment_validation_suite.py — DEV/SIM/LIVE separation tests."""
from __future__ import annotations
from tests.assertion_helpers import assert_true, assert_equal, assert_raises
from env.environment_guard import guard_environment_action, EnvironmentDenied
from env.environment_policy_loader import load_environment_policy_bundle
from env.promotion_gate_engine import evaluate_environment_promotion
from env.environment_routing_engine import tag_object_with_environment, apply_environment_routing_prefix

def run_environment_validation_suite() -> list[dict]:
    results=[]

    # DEV execution denied
    try: guard_environment_action("DEV","execute_ticket",require_execution_enabled=True); assert_true(False,"should raise")
    except EnvironmentDenied: pass
    results.append({"test":"DEV execution denied","status":"PASS"})

    # SIM execution denied
    try: guard_environment_action("SIM","execute_ticket",require_execution_enabled=True); assert_true(False,"should raise")
    except EnvironmentDenied: pass
    results.append({"test":"SIM execution denied","status":"PASS"})

    # LIVE execution allowed (no exception)
    guard_environment_action("LIVE","execute_ticket",require_execution_enabled=True)
    results.append({"test":"LIVE execution allowed","status":"PASS"})

    # DEV policy activation denied
    try: guard_environment_action("DEV","activate_policy",require_policy_activation_enabled=True); assert_true(False,"should raise")
    except EnvironmentDenied: pass
    results.append({"test":"DEV policy activation denied","status":"PASS"})

    # SIM→LIVE blocked without approval
    promo=evaluate_environment_promotion("SIM","LIVE",{"total_fail":0},[],approval_present=False)
    assert_true(not promo["promotion_allowed"],"no approval blocks LIVE promo")
    results.append({"test":"SIM→LIVE without approval blocked","status":"PASS"})

    # SIM→LIVE blocked with validation failures
    promo2=evaluate_environment_promotion("SIM","LIVE",{"total_fail":2},[],approval_present=True)
    assert_true(not promo2["promotion_allowed"],"validation failures block LIVE promo")
    results.append({"test":"SIM→LIVE with validation failures blocked","status":"PASS"})

    # SIM→LIVE allowed when clean
    promo3=evaluate_environment_promotion("SIM","LIVE",{"total_fail":0},[],approval_present=True)
    assert_true(promo3["promotion_allowed"],"valid promo allowed")
    results.append({"test":"SIM→LIVE with approval allowed","status":"PASS"})

    # Policy loader isolates environments
    reg=[
        {"policy_version_id":"SIM1","status":"LIVE","environment":"SIM","activated_utc":"2026-01-02","policy_bundle":{"sim":True}},
        {"policy_version_id":"LIV1","status":"LIVE","environment":"LIVE","activated_utc":"2026-01-02","policy_bundle":{"live":True}},
    ]
    live_b=load_environment_policy_bundle(reg,"LIVE")
    sim_b =load_environment_policy_bundle(reg,"SIM")
    assert_true(live_b.get("live") and not live_b.get("sim"),"LIVE loader returns LIVE policy only")
    assert_true(sim_b.get("sim")  and not sim_b.get("live"),"SIM loader returns SIM policy only")
    results.append({"test":"environment policy isolation","status":"PASS"})

    # Routing prefix and tagging
    assert_equal(apply_environment_routing_prefix("DEV","T1"),"DEV_T1","routing prefix correct")
    tagged=tag_object_with_environment({"id":"X"},"SIM")
    assert_equal(tagged["environment"],"SIM","object tagged with environment")
    results.append({"test":"environment routing and tagging","status":"PASS"})

    return results
