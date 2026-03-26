"""tests/engine_validation_suite.py — Playbook mapping and narrative tests."""
from __future__ import annotations
from tests.assertion_helpers import assert_true
from tests.fixture_factory import make_position_row
from analyst.narrative_engine import build_transition_narrative
from playbooks.playbook_matcher import build_playbook_match

def _pass(t): return {"test":t,"status":"PASS"}

def run_engine_validation_suite() -> list[dict]:
    results=[]
    row = make_position_row()
    pb = build_playbook_match(row)
    assert_true(pb["playbook_code"].startswith("PB"), "playbook matcher assigns PB code")
    results.append(_pass("playbook match"))

    row.update(pb); row["transition_rejected_candidates"]=[{"reason":"Timing gate blocked transition"}]
    narrative = build_transition_narrative(row)
    assert_true(bool(narrative.get("desk_note")), "narrative generates desk note")
    assert_true(len(narrative.get("winner_reasons",[])) > 0, "narrative has winner reasons")
    assert_true(bool(narrative.get("invalidation_summary")), "narrative has invalidation summary")
    results.append(_pass("narrative generation"))

    # Surface block maps to PB006
    row2 = make_position_row(transition_execution_surface_ok=False,
                             transition_timing_ok=True,transition_portfolio_fit_ok=True)
    pb2 = build_playbook_match(row2)
    assert_true(pb2["playbook_code"]=="PB006", f"surface block → PB006 (got {pb2['playbook_code']})")
    results.append(_pass("surface block maps to PB006"))

    return results
