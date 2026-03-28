"""engine/roll_logic.py — Same-side roll evaluation."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass
class RollAssessment:
    current_short_strike: float
    current_short_mid: float          # current close cost (bid)
    proposed_short_mid: float         # new short premium (mid)
    proposed_short_strike: float
    option_type: str
    campaign_recovered_pct: float
    next_gen_scores: list[float]       # premium of next-gen shorts for continuity

    roll_credit_est: float = 0.0
    net_credit_positive: bool = False
    continuity_score: float = 0.0
    strike_improved: bool = False
    approved: bool = False
    reason: str = ""

    def __post_init__(self):
        self.roll_credit_est = round(self.proposed_short_mid - self.current_short_mid, 4)
        self.net_credit_positive = self.roll_credit_est > 0

        # Strike improvement: for PUT, lower strike = safer; for CALL, higher = safer
        if self.option_type.upper() == "PUT":
            self.strike_improved = self.proposed_short_strike < self.current_short_strike
        else:
            self.strike_improved = self.proposed_short_strike > self.current_short_strike

        # Continuity: average of next-gen premiums as proxy for future roll viability
        if self.next_gen_scores:
            self.continuity_score = round(sum(self.next_gen_scores) / len(self.next_gen_scores), 4)

        # Approval: must produce net credit, campaign not already fully recovered
        reasons = []
        if not self.net_credit_positive:
            reasons.append(f"Roll credit ${self.roll_credit_est:.2f} is not positive")
        if self.campaign_recovered_pct >= 90.0:
            reasons.append("Campaign already 90%+ recovered — consider banking gains instead")
        if self.continuity_score < 0.50:
            reasons.append("Next-gen continuity weak — future rolls may not be available")

        self.approved = len(reasons) == 0
        self.reason = " | ".join(reasons) if reasons else "Approved same-side roll"

def assess_roll(current_short_strike: float, current_short_mid: float,
                proposed_short_mid: float, proposed_short_strike: float,
                option_type: str, campaign_recovered_pct: float,
                next_gen_premiums: list[float]) -> RollAssessment:
    return RollAssessment(current_short_strike=current_short_strike,
                           current_short_mid=current_short_mid,
                           proposed_short_mid=proposed_short_mid,
                           proposed_short_strike=proposed_short_strike,
                           option_type=option_type,
                           campaign_recovered_pct=campaign_recovered_pct,
                           next_gen_scores=next_gen_premiums)
