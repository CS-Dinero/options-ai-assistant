"""tracker/campaign_tracker.py — Campaign state, formulas, scaling decision, CSV export."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import csv, io, math

# ── Scaling constants ──────────────────────────────────────────────────────────
SAFETY_FACTOR        = 0.60   # never deploy more than 60% of mathematically allowed
MIN_ROLL_CREDIT      = 0.25   # roll credit below this = not truly golden
MIN_EM_CLEARANCE     = 0.50   # short must be at least 0.5x expected move away


@dataclass
class CampaignTracker:
    campaign_id: str
    symbol: str
    structure_type: str        # "CALENDAR" | "DIAGONAL"
    entry_date: str
    starting_capital: float
    entry_debit: float

    total_harvest_collected: float = 0.0
    total_roll_costs: float = 0.0
    spread_profit: float = 0.0
    contracts: int = 1

    # Live roll state — update these before calling scaling methods
    current_roll_credit: float = 0.0    # net credit available on next roll
    distance_to_strike: float = 999.0  # $distance from spot to short strike
    expected_move: float = 1.0         # 1-week expected move of underlying

    events: list[dict[str,Any]] = field(default_factory=list)

    # ── Computed fields ───────────────────────────────────────────────────────
    net_campaign_basis: float = 0.0
    campaign_recovered_pct: float = 0.0
    net_weekly_gain: float = 0.0
    true_weekly_return: float = 0.0
    excess_harvest: float = 0.0
    spread_funding_available: float = 0.0
    active_debit_capital: float = 0.0
    net_weekly_gain_per_contract: float = 0.0
    net_weekly_gain_total: float = 0.0
    true_weekly_return_total: float = 0.0

    def __post_init__(self):
        self.active_debit_capital = self.entry_debit
        self._recalculate()

    # ── Core accounting ───────────────────────────────────────────────────────
    def _recalculate(self):
        self.net_campaign_basis = round(
            self.entry_debit - self.total_harvest_collected + self.total_roll_costs, 6)
        self.campaign_recovered_pct = round(
            max(0.0, (self.entry_debit - self.net_campaign_basis) / max(0.01, self.entry_debit) * 100), 6)
        self.net_weekly_gain = round(
            self.total_harvest_collected + self.spread_profit - self.total_roll_costs, 6)
        self.true_weekly_return = round(
            self.net_weekly_gain / max(0.01, self.starting_capital) * 100, 6)
        self.active_debit_capital = max(0.0, round(self.net_campaign_basis, 6))
        self.excess_harvest = round(
            max(0.0, self.total_harvest_collected - self.total_roll_costs - self.entry_debit), 6)
        self.spread_funding_available = self.excess_harvest + round(self.spread_profit, 6)
        self.net_weekly_gain_per_contract = self.net_weekly_gain
        self.net_weekly_gain_total = round(self.net_weekly_gain * self.contracts, 6)
        self.true_weekly_return_total = round(
            self.net_weekly_gain_total / max(0.01, self.starting_capital) * 100, 6)

    # ── Event application ─────────────────────────────────────────────────────
    def apply_harvest(self, credit: float, date: str, note: str = "") -> "CampaignTracker":
        self.total_harvest_collected = round(self.total_harvest_collected + credit, 6)
        self.events.append({"type":"HARVEST","date":date,"credit":credit,"debit":0.0,"note":note})
        self._recalculate(); return self

    def apply_roll(self, close_cost: float, new_credit: float, date: str, note: str = "") -> "CampaignTracker":
        self.total_harvest_collected = round(self.total_harvest_collected + new_credit, 6)
        self.total_roll_costs = round(self.total_roll_costs + close_cost, 6)
        self.events.append({"type":"ROLL","date":date,"credit":new_credit,"debit":close_cost,"note":note})
        self._recalculate(); return self

    def apply_spread_profit(self, profit: float, date: str, note: str = "") -> "CampaignTracker":
        self.spread_profit = round(self.spread_profit + profit, 6)
        self.events.append({"type":"SPREAD_PROFIT","date":date,"credit":profit,"debit":0.0,"note":note})
        self._recalculate(); return self

    # ── Golden Harvest detection ──────────────────────────────────────────────
    def is_golden_harvest(self) -> bool:
        """
        True ONLY when all three conditions hold simultaneously:
          1. Basis is negative  — debit fully recovered AND excess exists
          2. Roll still credits — next roll produces meaningful net credit
          3. Structure safe     — short strike not threatened by expected move
        """
        basis_recovered   = self.net_campaign_basis < 0
        roll_still_works  = self.current_roll_credit >= MIN_ROLL_CREDIT
        structure_safe    = self.distance_to_strike >= (MIN_EM_CLEARANCE * self.expected_move)
        return basis_recovered and roll_still_works and structure_safe

    def golden_harvest_reason(self) -> str:
        """Returns plain-English explanation of what's blocking Golden Harvest."""
        if self.net_campaign_basis >= 0:
            remaining = round(self.net_campaign_basis, 2)
            return f"Basis not yet negative — ${remaining:.2f} remaining to recover"
        if self.current_roll_credit < MIN_ROLL_CREDIT:
            return (f"Roll credit ${self.current_roll_credit:.2f} below minimum ${MIN_ROLL_CREDIT:.2f} — "
                    f"short needs more time to decay")
        if self.distance_to_strike < (MIN_EM_CLEARANCE * self.expected_move):
            return (f"Short too close — distance ${self.distance_to_strike:.2f} vs "
                    f"min ${self.expected_move * MIN_EM_CLEARANCE:.2f} (0.5x EM)")
        return "All conditions met"

    # ── Scaling decision ──────────────────────────────────────────────────────
    def allowed_contracts(self) -> int:
        """Max contracts math allows — only computed when Golden Harvest is TRUE."""
        if not self.is_golden_harvest():
            return self.contracts  # no scaling until earned
        excess = abs(self.net_campaign_basis)  # negative basis = excess per contract
        return math.floor(self.contracts + (excess / max(0.001, self.entry_debit)))

    def safe_contracts(self) -> int:
        """Allowed contracts reduced by safety factor. This is the number you act on."""
        raw = self.allowed_contracts()
        scaled = math.floor(raw * SAFETY_FACTOR)
        return max(self.contracts, scaled)  # never reduce below current

    def scaling_decision(self) -> str:
        """Returns SCALE / HOLD / REDUCE — the one flag you need while on shift."""
        if not self.is_golden_harvest():
            if self.net_campaign_basis < 0 and self.current_roll_credit < MIN_ROLL_CREDIT:
                return "HOLD"   # golden but roll degraded — protect position
            return "HOLD"
        safe = self.safe_contracts()
        if safe > self.contracts:
            return "SCALE"
        return "HOLD"

    # ── Full decision block ───────────────────────────────────────────────────
    def decision_block(self) -> dict[str, Any]:
        """Everything the engine needs to act — one dict."""
        golden  = self.is_golden_harvest()
        allowed = self.allowed_contracts()
        safe    = self.safe_contracts()
        decision= self.scaling_decision()
        add_cts = max(0, safe - self.contracts)
        roi_debit = round(
            (self.net_weekly_gain * self.contracts * 100) /
            max(0.01, self.entry_debit * self.contracts * 100) * 100, 2)
        return {
            "golden_harvest":       golden,
            "golden_harvest_reason": self.golden_harvest_reason(),
            "decision":             decision,
            "current_contracts":    self.contracts,
            "allowed_contracts":    allowed,
            "safe_contracts":       safe,
            "contracts_to_add":     add_cts,
            "excess_harvest_total": round(self.excess_harvest * self.contracts * 100, 2),
            "spread_capital_avail": round(self.spread_funding_available * self.contracts * 100, 2),
            "roi_on_debit_pct":     roi_debit,
        }

    # ── Summary + printing ────────────────────────────────────────────────────
    def summary(self) -> dict[str,Any]:
        d = self.decision_block()
        return {
            "campaign_id":           self.campaign_id,
            "symbol":                self.symbol,
            "structure_type":        self.structure_type,
            "entry_date":            self.entry_date,
            "starting_capital":      self.starting_capital,
            "entry_debit":           self.entry_debit,
            "total_harvest_collected": self.total_harvest_collected,
            "total_roll_costs":      self.total_roll_costs,
            "spread_profit":         self.spread_profit,
            "net_campaign_basis":    self.net_campaign_basis,
            "campaign_recovered_pct": round(self.campaign_recovered_pct, 2),
            "active_debit_capital":  self.active_debit_capital,
            "excess_harvest":        self.excess_harvest,
            "spread_funding_available": self.spread_funding_available,
            "net_weekly_gain":       self.net_weekly_gain,
            "true_weekly_return_pct": round(self.true_weekly_return, 4),
            "event_count":           len(self.events),
            "contracts":             self.contracts,
            "net_weekly_gain_per_contract": self.net_weekly_gain_per_contract,
            "net_weekly_gain_total": self.net_weekly_gain_total,
            "true_weekly_return_total": round(self.true_weekly_return_total, 4),
            **d,
        }

    def print_summary(self):
        s = self.summary()
        d = self.decision_block()
        golden = d["golden_harvest"]

        STAR  = "★" if golden else " "
        RESET = ""

        print(f"\n{'═'*52}")
        print(f"  {STAR} {s['campaign_id']}  ({s['symbol']} {s['structure_type']})")
        print(f"  Entry: {s['entry_date']}  |  Capital: ${s['starting_capital']:,.0f}")
        print(f"{'─'*52}")
        print(f"  Entry debit:           ${s['entry_debit']:>8.2f}  x{s['contracts']} contracts")
        print(f"  Harvest collected:     ${s['total_harvest_collected']:>8.2f}")
        print(f"  Roll costs:            ${s['total_roll_costs']:>8.2f}")
        print(f"  Spread profit:         ${s['spread_profit']:>8.2f}")
        print(f"{'─'*52}")
        print(f"  Net campaign basis:    ${s['net_campaign_basis']:>8.2f}")
        print(f"  Recovered:              {s['campaign_recovered_pct']:>7.2f}%")
        print(f"{'─'*52}")
        print(f"  Excess harvest:        ${s['excess_harvest']:>8.2f}")
        print(f"  Spread capital avail:  ${s['spread_funding_available']:>8.2f}")
        print(f"  ROI on debit deployed: {d['roi_on_debit_pct']:>7.1f}%")
        print(f"{'═'*52}")
        gh_label = "TRUE  ★ GOLDEN HARVEST" if golden else "FALSE"
        print(f"  GOLDEN HARVEST:  {gh_label}")
        if not golden:
            print(f"  Reason:          {d['golden_harvest_reason']}")
        print(f"{'─'*52}")
        decision_symbol = {"SCALE":"↑ SCALE","HOLD":"→ HOLD","REDUCE":"↓ REDUCE"}.get(d["decision"], d["decision"])
        print(f"  DECISION:        {decision_symbol}")
        print(f"  Current:         {d['current_contracts']} contracts")
        if d["decision"] == "SCALE":
            print(f"  Allowed (math):  {d['allowed_contracts']} contracts")
            print(f"  Safe (60% rule): {d['safe_contracts']} contracts  ← ADD {d['contracts_to_add']}")
            print(f"  Spread capital:  ${d['spread_capital_avail']:.2f} available for credit spreads")
        print(f"{'═'*52}\n")

    @property
    def event_count(self) -> int:
        return len(self.events)

    def to_csv_row(self) -> dict[str,Any]:
        return self.summary()

    def to_csv_string(self) -> str:
        row = self.to_csv_row()
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=list(row.keys()))
        writer.writeheader(); writer.writerow(row)
        return buf.getvalue()
