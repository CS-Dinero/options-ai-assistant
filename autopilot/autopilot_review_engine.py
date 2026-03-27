"""autopilot/autopilot_review_engine.py — Creates review tasks when automation boundaries are challenged."""
from __future__ import annotations
from typing import Any
from review.review_packet_builder import build_review_packet
from review.review_priority_engine import assign_review_priority
from review.review_assignment_engine import assign_review_role

def build_autopilot_boundary_review(environment: str, request: dict[str,Any],
                                     guard_result: dict[str,Any]) -> dict[str,Any]:
    pkt=build_review_packet("POLICY_SIMULATION_REVIEW",environment,
                             request.get("request_id","UNKNOWN"),"AUTOPILOT_BOUNDARY",
                             "Autopilot boundary exception review",
                             f"Requested {guard_result.get('requested_authority')} exceeds allowed {guard_result.get('maximum_allowed_authority')} for {guard_result.get('action_family')} in {environment}.",
                             {"request":request,"guard_result":guard_result},
                             "Should this request be revised, blocked, or explicitly exception-reviewed?")
    return assign_review_role(assign_review_priority(pkt))
