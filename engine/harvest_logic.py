"""engine/harvest_logic.py — Harvest threshold detection and recommendation."""
from __future__ import annotations
from dataclasses import dataclass

HARVEST_ZONE_LOW  = 0.30   # 30% of short premium captured = start of harvest zone
HARVEST_ZONE_HIGH = 0.50   # 50% = strong harvest

@dataclass
class HarvestAssessment:
    short_premium_at_entry: float
    current_short_mid: float
    campaign_recovered_pct: float

    premium_captured_pct: float = 0.0
    in_harvest_zone: bool = False
    harvest_strength: str = "NONE"    # NONE | WEAK | STRONG
    basis_improving: bool = False
    recommendation: str = ""

    def __post_init__(self):
        if self.short_premium_at_entry > 0:
            captured = self.short_premium_at_entry - self.current_short_mid
            self.premium_captured_pct = round(captured / self.short_premium_at_entry, 4)

        self.in_harvest_zone = self.premium_captured_pct >= HARVEST_ZONE_LOW
        self.basis_improving = self.campaign_recovered_pct > 0

        if self.premium_captured_pct >= HARVEST_ZONE_HIGH:
            self.harvest_strength = "STRONG"
            self.recommendation = "Harvest now or roll for continuation credit."
        elif self.premium_captured_pct >= HARVEST_ZONE_LOW:
            self.harvest_strength = "WEAK"
            self.recommendation = "In harvest zone — monitor. Roll if net credit available."
        else:
            self.harvest_strength = "NONE"
            self.recommendation = "Not in harvest zone yet. Hold."

def assess_harvest(short_premium_at_entry: float, current_short_mid: float,
                   campaign_recovered_pct: float) -> HarvestAssessment:
    return HarvestAssessment(short_premium_at_entry=short_premium_at_entry,
                              current_short_mid=current_short_mid,
                              campaign_recovered_pct=campaign_recovered_pct)
