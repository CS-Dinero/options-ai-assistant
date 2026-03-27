"""doctrine/doctrine_review_engine.py — Creates review tasks for doctrine conflicts."""
from __future__ import annotations
from typing import Any
from review.review_packet_builder import build_review_packet
from review.review_priority_engine import assign_review_priority
from review.review_assignment_engine import assign_review_role

def build_doctrine_review(environment: str, proposal: dict[str,Any],
                           doctrine_guard_result: dict[str,Any]) -> dict[str,Any]:
    pkt=build_review_packet("POLICY_SIMULATION_REVIEW",environment,
                             proposal.get("proposal_id","UNKNOWN"),"DOCTRINE_GUARD",
                             "Doctrine exception or conflict review",
                             f"Violations: {'; '.join(doctrine_guard_result.get('violations',[]))}",
                             {"proposal":proposal,"doctrine_guard_result":doctrine_guard_result},
                             "Should this proposal be blocked, revised, or granted a doctrine exception?")
    return assign_review_role(assign_review_priority(pkt))
