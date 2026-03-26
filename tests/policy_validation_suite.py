"""tests/policy_validation_suite.py — Policy override non-mutation and rollback tests."""
from __future__ import annotations
from copy import deepcopy
from tests.assertion_helpers import assert_equal, assert_true
from tests.fixture_factory import make_policy_bundle
from policy.policy_override_engine import apply_policy_overrides
from control.policy_version_registry import create_policy_version, append_policy_version
from control.policy_activation_engine import activate_policy_version
from control.policy_rollback_engine import rollback_to_policy_version
from control.live_policy_loader import load_live_policy_bundle

def _pass(test): return {"test":test,"status":"PASS"}

def run_policy_validation_suite() -> list[dict]:
    results=[]
    live = make_policy_bundle()
    original_status = deepcopy(live["playbook_policy_registry"]["PB002"]["status"])

    sim = apply_policy_overrides(live, {"playbook_status_overrides":{"PB002":"DEMOTED"}})
    assert_equal(live["playbook_policy_registry"]["PB002"]["status"], original_status, "live bundle not mutated")
    assert_equal(sim["playbook_policy_registry"]["PB002"]["status"], "DEMOTED", "sim reflects override")
    results.append(_pass("simulation non-mutating"))

    # Version lifecycle
    v1 = create_policy_version(make_policy_bundle(), status="APPROVED", notes="v1")
    reg = append_policy_version([], v1)
    reg = activate_policy_version(reg, v1["policy_version_id"], "admin")
    live_b = load_live_policy_bundle(reg)
    assert_true(bool(live_b), "live policy loader returns bundle after activation")
    results.append(_pass("policy version activation and live load"))

    # Rollback
    v2 = create_policy_version(make_policy_bundle(), status="APPROVED", notes="v2")
    reg = append_policy_version(reg, v2)
    reg = activate_policy_version(reg, v2["policy_version_id"], "admin")
    reg = rollback_to_policy_version(reg, v1["policy_version_id"], "admin", "test rollback")
    statuses = {v["policy_version_id"]: v["status"] for v in reg}
    assert_equal(statuses[v1["policy_version_id"]], "LIVE", "v1 re-activated after rollback")
    assert_equal(statuses[v2["policy_version_id"]], "ROLLED_BACK", "v2 marked rolled back")
    results.append(_pass("rollback restores prior version"))

    return results
