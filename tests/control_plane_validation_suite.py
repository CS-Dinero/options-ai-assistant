"""tests/control_plane_validation_suite.py — Permission, approval, activation, rollback tests."""
from __future__ import annotations
from tests.assertion_helpers import assert_equal, assert_true
from tests.fixture_factory import make_policy_bundle, make_session_context
from auth.action_guard import guard_action, PermissionDenied
from auth.role_resolver import resolve_permissions

def _pass(t): return {"test":t,"status":"PASS"}

def run_control_plane_validation_suite() -> list[dict]:
    results=[]
    # Analyst cannot approve
    analyst = make_session_context(roles=["ANALYST"])
    denied=False
    try: guard_action(analyst,"APPROVE_POLICY","approve_policy")
    except PermissionDenied: denied=True
    assert_true(denied, "analyst denied APPROVE_POLICY")
    results.append(_pass("analyst denied approve"))

    # Trader cannot activate policy
    trader = make_session_context(roles=["TRADER_OPERATOR"])
    denied=False
    try: guard_action(trader,"ACTIVATE_POLICY","activate_policy")
    except PermissionDenied: denied=True
    assert_true(denied, "trader denied ACTIVATE_POLICY")
    results.append(_pass("trader denied activate"))

    # Admin can do everything
    admin = make_session_context(roles=["ADMIN"])
    perms = resolve_permissions(admin)
    for p in ["APPROVE_POLICY","ACTIVATE_POLICY","ROLLBACK_POLICY","EXECUTE_TICKET"]:
        assert_true(p in perms, f"admin has {p}")
    results.append(_pass("admin has full permissions"))

    # Mixed role: APPROVER + TRADER_OPERATOR
    dual = make_session_context(roles=["APPROVER","TRADER_OPERATOR"])
    dual_perms = resolve_permissions(dual)
    assert_true("APPROVE_POLICY" in dual_perms, "dual role has APPROVE_POLICY")
    assert_true("EXECUTE_TICKET" in dual_perms, "dual role has EXECUTE_TICKET")
    results.append(_pass("mixed role combined permissions"))

    return results
