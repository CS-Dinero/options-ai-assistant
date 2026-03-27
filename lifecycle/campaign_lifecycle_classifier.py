"""lifecycle/campaign_lifecycle_classifier.py — Coordinates all campaign lifecycle engines."""
from __future__ import annotations
from typing import Any
from campaigns.campaign_state_engine import CampaignStateInput, classify_campaign_state

def build_campaign_lifecycle_decision(state_input: CampaignStateInput,
                                       roll_output: dict|None=None,
                                       defense_output: dict|None=None,
                                       flip_output: dict|None=None,
                                       collapse_output: dict|None=None,
                                       harvest_min_pct: float=30.0,
                                       harvest_target_pct: float=40.0) -> dict[str,Any]:
    decision=classify_campaign_state(state_input,harvest_min_pct,harvest_target_pct)
    return {"campaign_state":decision.campaign_state,"campaign_action":decision.campaign_action,
            "campaign_urgency":decision.campaign_urgency,"campaign_reason":decision.campaign_reason,
            "state_score":decision.state_score,
            "roll_output":roll_output or {},"defense_output":defense_output or {},
            "flip_output":flip_output or {},"collapse_output":collapse_output or {}}
