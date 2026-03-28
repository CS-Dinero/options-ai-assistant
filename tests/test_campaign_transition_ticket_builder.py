"""tests/test_campaign_transition_ticket_builder.py — Ticket drafting correctness."""
from execution.transition_ticket_builder import (
    build_campaign_transition_ticket, campaign_transition_ticket_to_dict,
)
from tests.fixtures.deep_itm_campaign_fixtures import ticket_input_roll_ready

def test_campaign_ticket_builds():
    ticket=build_campaign_transition_ticket(ticket_input_roll_ready())
    assert ticket.campaign_id == "cmp_tsla_001"
    assert ticket.selected_path == "ROLL_SAME_SIDE"
    assert ticket.projected_credit == 0.70
    assert ticket.projected_basis_after_action == 3.60
    assert ticket.future_roll_score == 80.0
    assert ticket.authority == "AUTO_DRAFT"
    assert ticket.ticket_type == "CAMPAIGN_TRANSITION_TICKET"
    assert any("LIVE tickets are draft-only" in w or "draft-only" in w.lower() for w in ticket.warnings)

def test_ticket_campaign_snapshot():
    ticket=build_campaign_transition_ticket(ticket_input_roll_ready())
    snap=ticket.campaign_snapshot
    assert snap["opening_debit"] == 8.0
    assert snap["realized_credit_collected"] == 4.7
    assert snap["net_campaign_basis"] == 4.3
    assert snap["campaign_recovered_pct"] == 46.25
    assert snap["campaign_cycle_count"] == 2

def test_ticket_execution_plan():
    ticket=build_campaign_transition_ticket(ticket_input_roll_ready())
    ep=ticket.execution_plan
    assert ep["selected_path_code"] == "ROLL_SAME_SIDE"
    assert ep["projected_credit"] == 0.70
    assert ep["future_roll_score"] == 80.0
    assert ep["proposed_short_strike"] == 240.0
    assert ep["proposed_short_expiry"] == "2026-04-17"

def test_ticket_to_dict():
    ticket=build_campaign_transition_ticket(ticket_input_roll_ready())
    d=campaign_transition_ticket_to_dict(ticket)
    assert isinstance(d,dict)
    assert d["campaign_id"] == "cmp_tsla_001"
    assert d["selected_path"] == "ROLL_SAME_SIDE"
    assert d["authority"] == "AUTO_DRAFT"
