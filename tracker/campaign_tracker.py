"""tracker/campaign_tracker.py — Campaign state, formulas, summary, CSV export."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any
import csv, io

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

    events: list[dict[str,Any]] = field(default_factory=list)

    # ── Computed (call update() after any event) ─────────────────────────────
    net_campaign_basis: float = 0.0
    campaign_recovered_pct: float = 0.0
    net_weekly_gain: float = 0.0
    true_weekly_return: float = 0.0
    excess_harvest: float = 0.0
    spread_funding_available: float = 0.0
    active_debit_capital: float = 0.0

    def __post_init__(self):
        self.active_debit_capital = self.entry_debit
        self._recalculate()

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
        # Excess harvest = credits collected beyond full debit recovery
        self.excess_harvest = round(
            max(0.0, self.total_harvest_collected - self.total_roll_costs - self.entry_debit), 6)
        self.spread_funding_available = self.excess_harvest + round(self.spread_profit, 6)

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

    def summary(self) -> dict[str,Any]:
        return {
            "campaign_id": self.campaign_id,
            "symbol": self.symbol,
            "structure_type": self.structure_type,
            "entry_date": self.entry_date,
            "starting_capital": self.starting_capital,
            "entry_debit": self.entry_debit,
            "total_harvest_collected": self.total_harvest_collected,
            "total_roll_costs": self.total_roll_costs,
            "spread_profit": self.spread_profit,
            "net_campaign_basis": self.net_campaign_basis,
            "campaign_recovered_pct": round(self.campaign_recovered_pct, 2),
            "active_debit_capital": self.active_debit_capital,
            "excess_harvest": self.excess_harvest,
            "spread_funding_available": self.spread_funding_available,
            "net_weekly_gain": self.net_weekly_gain,
            "true_weekly_return_pct": round(self.true_weekly_return, 4),
            "event_count": len(self.events),
        }

    def print_summary(self):
        s = self.summary()
        print(f"\n{'─'*50}")
        print(f"  Campaign: {s['campaign_id']}  ({s['symbol']} {s['structure_type']})")
        print(f"  Entry date: {s['entry_date']}  |  Starting capital: ${s['starting_capital']:,.2f}")
        print(f"{'─'*50}")
        print(f"  Entry debit:           ${s['entry_debit']:>8.2f}")
        print(f"  Harvest collected:     ${s['total_harvest_collected']:>8.2f}")
        print(f"  Roll costs:            ${s['total_roll_costs']:>8.2f}")
        print(f"  Spread profit:         ${s['spread_profit']:>8.2f}")
        print(f"{'─'*50}")
        print(f"  Net campaign basis:    ${s['net_campaign_basis']:>8.2f}")
        print(f"  Recovered:              {s['campaign_recovered_pct']:>7.2f}%")
        print(f"  Active debit capital:  ${s['active_debit_capital']:>8.2f}")
        print(f"{'─'*50}")
        print(f"  Excess harvest:        ${s['excess_harvest']:>8.2f}")
        print(f"  Spread funding avail:  ${s['spread_funding_available']:>8.2f}")
        print(f"{'─'*50}")
        print(f"  Net weekly gain:       ${s['net_weekly_gain']:>8.2f}")
        print(f"  True weekly return:     {s['true_weekly_return_pct']:>7.4f}%")
        print(f"{'─'*50}\n")

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
