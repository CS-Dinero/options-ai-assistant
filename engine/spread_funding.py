"""engine/spread_funding.py — Excess harvest accounting and spread capital calculation."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass
class SpreadFundingAssessment:
    entry_debit: float
    total_harvest_collected: float
    total_roll_costs: float
    spread_profit: float

    net_campaign_basis: float = 0.0
    recovered_amount: float = 0.0
    excess_harvest: float = 0.0
    spread_funding_available: float = 0.0
    can_fund_spreads: bool = False
    recommendation: str = ""

    def __post_init__(self):
        self.net_campaign_basis = round(
            self.entry_debit - self.total_harvest_collected + self.total_roll_costs, 6)
        self.recovered_amount = round(
            max(0.0, self.entry_debit - self.net_campaign_basis), 6)

        # Only credits BEYOND full debit recovery count as deployable
        # net_campaigns_basis < 0 means we've recovered more than we paid
        self.excess_harvest = round(
            max(0.0, -self.net_campaign_basis), 6)
        self.spread_funding_available = round(self.excess_harvest + self.spread_profit, 6)
        self.can_fund_spreads = self.spread_funding_available > 0.25  # min meaningful spread cost

        if self.can_fund_spreads:
            self.recommendation = (f"${self.spread_funding_available:.2f} available for spreads. "
                                   f"Only deploy excess — do not count active debit recovery as free capital.")
        elif self.excess_harvest > 0:
            self.recommendation = (f"${self.excess_harvest:.2f} excess, but below $0.25 spread threshold. "
                                   f"Continue rolling to build more.")
        else:
            self.recommendation = (f"Debit not fully recovered yet (basis=${self.net_campaign_basis:.2f}). "
                                   f"Focus on harvest before funding spreads.")

def assess_spread_funding(entry_debit: float, total_harvest_collected: float,
                           total_roll_costs: float, spread_profit: float = 0.0) -> SpreadFundingAssessment:
    return SpreadFundingAssessment(entry_debit=entry_debit,
                                    total_harvest_collected=total_harvest_collected,
                                    total_roll_costs=total_roll_costs,
                                    spread_profit=spread_profit)
