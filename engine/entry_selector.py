"""engine/entry_selector.py — Deep ITM entry evaluation and cheapness scoring."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass
class EntryCandidate:
    symbol: str
    structure_type: str        # "CALENDAR" | "DIAGONAL"
    option_type: str           # "PUT" | "CALL"
    long_strike: float
    short_strike: float
    long_dte: int
    short_dte: int
    long_mid: float
    short_mid: float
    spot_price: float

    # Computed
    entry_net_debit: float = 0.0
    long_intrinsic: float = 0.0
    long_extrinsic: float = 0.0
    strike_width: float = 0.0
    debit_width_ratio: float = 0.0
    projected_roll_credits: float = 0.0
    recovery_ratio: float = 0.0
    cheapness_score: float = 0.0
    valid: bool = False
    reason: str = ""

    def __post_init__(self):
        self._evaluate()

    def _evaluate(self):
        self.entry_net_debit = round(self.long_mid - self.short_mid, 4)
        self.strike_width = abs(self.long_strike - self.short_strike)

        if self.option_type.upper() == "PUT":
            self.long_intrinsic = max(0.0, self.long_strike - self.spot_price)
        else:
            self.long_intrinsic = max(0.0, self.spot_price - self.long_strike)

        self.long_extrinsic = round(max(0.0, self.long_mid - self.long_intrinsic), 4)
        self.debit_width_ratio = round(self.entry_net_debit / max(0.01, self.strike_width), 4)

        if self.projected_roll_credits > 0:
            self.recovery_ratio = round(self.projected_roll_credits / max(0.01, self.entry_net_debit), 4)

        # Cheapness score: lower debit/width = better, lower extrinsic = better, higher recovery = better
        width_score   = max(0.0, 100 - self.debit_width_ratio * 250)   # 0.40 ratio → 0
        extrinsic_score = max(0.0, 100 - self.long_extrinsic * 10)    # $10 extrinsic → 0
        recovery_score  = min(100.0, self.recovery_ratio * 70)         # 1.43 ratio → 100
        self.cheapness_score = round(0.35*width_score + 0.35*extrinsic_score + 0.30*recovery_score, 2)

        # Validation rules
        reasons = []
        if self.debit_width_ratio > 0.40:
            reasons.append(f"Debit/width ratio {self.debit_width_ratio:.2f} > 0.40 — too expensive")
        if self.long_extrinsic > 8.0:
            reasons.append(f"Long extrinsic ${self.long_extrinsic:.2f} > $8 — overpaying for time")
        if self.long_dte < 30 or self.long_dte > 90:
            reasons.append(f"Long DTE {self.long_dte} outside 30-90 range")
        if self.short_dte < 5 or self.short_dte > 21:
            reasons.append(f"Short DTE {self.short_dte} outside 5-21 range")
        if self.entry_net_debit <= 0:
            reasons.append("Net debit is zero or credit — structure invalid")

        self.valid = len(reasons) == 0
        self.reason = " | ".join(reasons) if reasons else "Valid deep ITM entry"

def evaluate_entry(symbol: str, structure_type: str, option_type: str,
                   long_strike: float, short_strike: float, long_dte: int, short_dte: int,
                   long_mid: float, short_mid: float, spot_price: float,
                   projected_roll_credits: float = 0.0) -> EntryCandidate:
    c = EntryCandidate(symbol=symbol, structure_type=structure_type, option_type=option_type,
                       long_strike=long_strike, short_strike=short_strike,
                       long_dte=long_dte, short_dte=short_dte, long_mid=long_mid,
                       short_mid=short_mid, spot_price=spot_price)
    c.projected_roll_credits = projected_roll_credits
    c._evaluate()
    return c
