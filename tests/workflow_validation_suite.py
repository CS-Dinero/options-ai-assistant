"""tests/workflow_validation_suite.py — Lifecycle integrity tests."""
from __future__ import annotations
from tests.assertion_helpers import assert_equal, assert_true, assert_raises
from workflow.workflow_engine import apply_state_transition
from workflow.workflow_guard import InvalidStateTransition

def _pass(test): return {"test":test,"status":"PASS"}

def run_workflow_validation_suite() -> list[dict]:
    results=[]
    # Legal: DRAFT → READY
    updated,event = apply_state_transition({"id":"T1","state":"DRAFT"},"EXECUTION_TICKET","READY","tester")
    assert_equal(updated["state"],"READY","ticket DRAFT→READY")
    assert_equal(event["from_state"],"DRAFT","event records old state")
    results.append(_pass("EXECUTION_TICKET DRAFT→READY"))

    # Illegal: DRAFT → APPROVED directly for change request
    assert_raises(InvalidStateTransition, apply_state_transition,
                  {"id":"CR1","state":"DRAFT"},"POLICY_CHANGE_REQUEST","APPROVED","tester")
    results.append(_pass("POLICY_CHANGE_REQUEST DRAFT→APPROVED blocked"))

    # Illegal: POLICY_VERSION DRAFT → LIVE
    assert_raises(InvalidStateTransition, apply_state_transition,
                  {"policy_version_id":"V1","state":"DRAFT"},"POLICY_VERSION","LIVE","tester")
    results.append(_pass("POLICY_VERSION DRAFT→LIVE blocked"))

    # Legal journal lifecycle
    j = {"journal_id":"J1","state":"PENDING_OUTCOME"}
    j,_ = apply_state_transition(j,"TRANSITION_JOURNAL","EXECUTED","tester")
    j,_ = apply_state_transition(j,"TRANSITION_JOURNAL","EVALUATED","tester")
    assert_equal(j["state"],"EVALUATED","journal PENDING→EXECUTED→EVALUATED")
    results.append(_pass("TRANSITION_JOURNAL full lifecycle"))

    # Terminal state stays terminal
    assert_raises(InvalidStateTransition, apply_state_transition,
                  {"id":"T2","state":"EXECUTED"},"EXECUTION_TICKET","READY","tester")
    results.append(_pass("terminal state blocks further transitions"))

    return results
