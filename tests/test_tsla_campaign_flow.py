"""tests/test_tsla_campaign_flow.py — One deterministic TSLA end-to-end walkthrough.

TSLA at $250. Deep ITM put calendar. $8.00 entry debit.
Proves: entry → harvest → roll → tracking → spread funding decision.
"""
import sys; sys.path.insert(0,'.')

from tracker.campaign_tracker import CampaignTracker
from engine.entry_selector import evaluate_entry
from engine.harvest_logic import assess_harvest
from engine.roll_logic import assess_roll
from engine.spread_funding import assess_spread_funding


# ── Fixed TSLA fixtures ───────────────────────────────────────────────────────
SPOT        = 250.0
CAPITAL     = 25_000.0
ENTRY_DEBIT = 8.00      # long put 270 mid $23.00 - short put 245 mid $15.00
SHORT_PREM  = 15.00     # short put premium at entry
LONG_MID    = 23.00
SHORT_MID   = 15.00


def test_1_entry_evaluation():
    """Entry at $8.00 debit on a 270/245 put calendar should be valid and cheap."""
    entry = evaluate_entry(
        symbol="TSLA", structure_type="CALENDAR", option_type="PUT",
        long_strike=270.0, short_strike=245.0, long_dte=45, short_dte=10,
        long_mid=LONG_MID, short_mid=SHORT_MID, spot_price=SPOT,
        projected_roll_credits=10.50,
    )
    assert entry.valid, f"Entry should be valid: {entry.reason}"
    assert abs(entry.entry_net_debit - 8.00) < 0.01
    assert abs(entry.long_intrinsic - 20.00) < 0.01   # 270 - 250 = 20
    assert abs(entry.long_extrinsic - 3.00) < 0.01    # 23 - 20 = 3
    assert abs(entry.debit_width_ratio - 0.32) < 0.01  # 8/25 = 0.32
    assert abs(entry.recovery_ratio - 1.3125) < 0.01   # 10.50/8.00
    assert entry.cheapness_score > 55
    return entry


def test_2_tracker_initializes():
    """Tracker starts clean with correct formula outputs."""
    t = CampaignTracker(
        campaign_id="cmp_tsla_001", symbol="TSLA", structure_type="CALENDAR",
        entry_date="2026-04-01", starting_capital=CAPITAL, entry_debit=ENTRY_DEBIT,
    )
    assert t.net_campaign_basis == ENTRY_DEBIT
    assert t.campaign_recovered_pct == 0.0
    assert t.spread_funding_available == 0.0
    assert t.active_debit_capital == ENTRY_DEBIT
    return t


def test_3_harvest_assessment():
    """After short put decays to $10.50, we're 30% in harvest zone."""
    h = assess_harvest(
        short_premium_at_entry=SHORT_PREM,
        current_short_mid=10.50,    # decayed $4.50 from $15.00
        campaign_recovered_pct=0.0,
    )
    assert abs(h.premium_captured_pct - 0.30) < 0.01   # $4.50/$15 = 30%
    assert h.in_harvest_zone
    assert h.harvest_strength == "WEAK"
    return h


def test_4_harvest_event_applied():
    """Harvesting $2.50 credit reduces basis and improves recovery."""
    t = CampaignTracker(
        campaign_id="cmp_tsla_001", symbol="TSLA", structure_type="CALENDAR",
        entry_date="2026-04-01", starting_capital=CAPITAL, entry_debit=ENTRY_DEBIT,
    )
    t.apply_harvest(credit=2.50, date="2026-04-08", note="Short put expired worthless, harvest $2.50")

    assert abs(t.total_harvest_collected - 2.50) < 1e-5
    # formula: 8.00 - 2.50 + 0.00 = 5.50
    assert abs(t.net_campaign_basis - 5.50) < 1e-5, f"basis={t.net_campaign_basis}"
    assert abs(t.campaign_recovered_pct - 31.25) < 0.01
    assert t.spread_funding_available == 0.0   # still in debit recovery
    return t


def test_5_roll_assessment():
    """Rolling: close current at $1.00, sell next at $1.80 → $0.80 net credit."""
    r = assess_roll(
        current_short_strike=245.0, current_short_mid=1.00,
        proposed_short_mid=1.80, proposed_short_strike=240.0,
        option_type="PUT", campaign_recovered_pct=31.25,
        next_gen_premiums=[1.70, 1.90, 2.10],   # future roll viability
    )
    assert r.approved, f"Roll should be approved: {r.reason}"
    assert abs(r.roll_credit_est - 0.80) < 0.01
    assert r.net_credit_positive
    assert r.strike_improved   # 240 < 245, safer for PUT
    assert r.continuity_score > 1.0


def test_6_roll_event_applied():
    """After harvest then roll: basis drops further, recovery climbs."""
    t = CampaignTracker(
        campaign_id="cmp_tsla_001", symbol="TSLA", structure_type="CALENDAR",
        entry_date="2026-04-01", starting_capital=CAPITAL, entry_debit=ENTRY_DEBIT,
    )
    t.apply_harvest(credit=2.50, date="2026-04-08")
    t.apply_roll(close_cost=1.00, new_credit=2.20, date="2026-04-15",
                  note="Rolled PUT 245→240, +$2.20 credit, -$1.00 close")

    # formula: 8.00 - (2.50+2.20) + 1.00 = 8.00 - 4.70 + 1.00 = 4.30
    assert abs(t.net_campaign_basis - 4.30) < 1e-5, f"basis={t.net_campaign_basis}"
    assert abs(t.campaign_recovered_pct - 46.25) < 0.01
    assert t.spread_funding_available == 0.0   # still in recovery
    assert t.event_count == 2
    return t


def test_7_spread_funding_assessment():
    """Spread funding only unlocks when excess harvest exceeds full debit recovery."""
    # Still in recovery (basis $4.30) — no spread funding
    sf_partial = assess_spread_funding(
        entry_debit=8.00, total_harvest_collected=4.70,
        total_roll_costs=1.00, spread_profit=0.0,
    )
    assert sf_partial.can_fund_spreads is False
    assert sf_partial.excess_harvest == 0.0
    assert "not fully recovered" in sf_partial.recommendation.lower() or "basis" in sf_partial.recommendation.lower()

    # Fully recovered + excess (collected 9.50, costs 0.50, basis = -1.00)
    sf_full = assess_spread_funding(
        entry_debit=8.00, total_harvest_collected=9.50,
        total_roll_costs=0.50, spread_profit=0.0,
    )
    assert sf_full.can_fund_spreads is True
    assert abs(sf_full.excess_harvest - 1.00) < 0.01   # 9.50 - 0.50 - 8.00 = 1.00
    assert sf_full.spread_funding_available >= 1.00


def test_8_full_tsla_walkthrough():
    """Complete flow: entry → harvest → roll → second roll → check spread funding."""
    t = CampaignTracker(
        campaign_id="cmp_tsla_001", symbol="TSLA", structure_type="CALENDAR",
        entry_date="2026-04-01", starting_capital=CAPITAL, entry_debit=ENTRY_DEBIT,
    )

    # Week 1: harvest
    t.apply_harvest(2.50, "2026-04-08", "Cycle 1 harvest")
    # Week 2: roll
    t.apply_roll(1.00, 2.20, "2026-04-15", "Roll PUT 245→240")
    # Week 3: roll again
    t.apply_roll(0.85, 2.10, "2026-04-22", "Roll PUT 240→237")

    s = t.summary()

    # Math: 8.00 - (2.50+2.20+2.10) + (1.00+0.85) = 8.00 - 6.80 + 1.85 = 3.05
    assert abs(s["net_campaign_basis"] - 3.05) < 0.01, f"basis={s['net_campaign_basis']}"
    assert s["campaign_recovered_pct"] > 60.0       # > 60% recovered
    assert s["event_count"] == 3
    assert s["spread_funding_available"] == 0.0     # still in recovery at $3.05 basis
    # net_weekly_gain counts harvest credits, which are real P&L even before full recovery
    # The campaign is still in debit (basis $3.05) but harvested credits exceed roll costs
    assert s["net_campaign_basis"] > 0.0            # still in debit — not done yet
    assert s["net_weekly_gain"] > 0.0               # net credits earned so far

    t.print_summary()
    return s


# ── Runner ────────────────────────────────────────────────────────────────────
TESTS = [
    ("1 Entry evaluation",     test_1_entry_evaluation),
    ("2 Tracker initializes",  test_2_tracker_initializes),
    ("3 Harvest assessment",   test_3_harvest_assessment),
    ("4 Harvest event",        test_4_harvest_event_applied),
    ("5 Roll assessment",      test_5_roll_assessment),
    ("6 Roll event",           test_6_roll_event_applied),
    ("7 Spread funding",       test_7_spread_funding_assessment),
    ("8 Full TSLA walkthrough",test_8_full_tsla_walkthrough),
]

if __name__ == "__main__":
    passed=0; failed=0
    print(f"\n{'='*55}")
    print("TSLA CAMPAIGN FLOW — TRACKER + ENGINE")
    print(f"{'='*55}")
    for name,fn in TESTS:
        try:
            fn(); passed+=1; print(f"  ✓ {name}")
        except Exception as e:
            failed+=1; print(f"  ✗ {name}: {e}")
    print(f"\n{'='*55}")
    print(f"RESULT: {passed} passed | {failed} failed")
    print(f"{'='*55}")
