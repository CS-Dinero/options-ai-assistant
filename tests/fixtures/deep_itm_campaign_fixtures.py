"""tests/fixtures/deep_itm_campaign_fixtures.py — Ready-to-paste fixtures for DEEP_ITM_CAMPAIGN tests."""
from __future__ import annotations
from scanner.deep_itm_entry_filters import OptionLegQuote
from scanner.deep_itm_calendar_scanner import MarketContextLite
from compare.campaign_path_ranker import RankedPath
from campaigns.campaign_basis_ledger import CampaignLedgerSnapshot
from campaigns.campaign_state_engine import CampaignStateDecision
from lifecycle.campaign_lifecycle_classifier import CampaignLifecycleDecision
from portfolio.campaign_queue_engine import CampaignQueueContext
from workspace.path_workspace_builder import CampaignWorkspaceInput
from execution.transition_ticket_builder import CampaignTransitionTicketInput

# ─── Market context ───────────────────────────────────────────────────────────
def tsla_neutral_context() -> MarketContextLite:
    return MarketContextLite(symbol="TSLA",spot_price=250.0,expected_move=12.0,
        iv_percentile=48.0,gamma_regime="POSITIVE",environment="NEUTRAL_TIME_SPREADS",
        regime_alignment_score=85.0,as_of_date="2026-01-24")

def tsla_high_vol_context() -> MarketContextLite:
    return MarketContextLite(symbol="TSLA",spot_price=250.0,expected_move=20.0,
        iv_percentile=82.0,gamma_regime="NEGATIVE",environment="HIGH_VOL_UNSTABLE",
        regime_alignment_score=30.0,as_of_date="2026-01-24")

# ─── Option leg quotes ────────────────────────────────────────────────────────
def long_put_deep_itm_valid() -> OptionLegQuote:
    return OptionLegQuote("TSLA","PUT","2026-05-15",270.0,22.5,23.5,23.0,-0.82,500,40)

def short_put_valid() -> OptionLegQuote:
    return OptionLegQuote("TSLA","PUT","2026-04-10",245.0,15.0,16.0,15.5,-0.32,700,60)

def long_put_expensive() -> OptionLegQuote:
    return OptionLegQuote("TSLA","PUT","2026-05-15",270.0,29.5,30.5,30.0,-0.82,500,40)

def next_generation_short_puts_good() -> list[OptionLegQuote]:
    return [OptionLegQuote("TSLA","PUT","2026-04-17",245.0,2.00,2.40,2.20,-0.31,1000,90),
            OptionLegQuote("TSLA","PUT","2026-04-17",240.0,1.70,1.90,1.80,-0.25,800,75),
            OptionLegQuote("TSLA","PUT","2026-04-24",245.0,2.20,2.60,2.40,-0.33,900,88)]

def next_generation_short_puts_weak() -> list[OptionLegQuote]:
    return [OptionLegQuote("TSLA","PUT","2026-04-17",240.0,0.35,0.45,0.40,-0.12,40,3),
            OptionLegQuote("TSLA","PUT","2026-04-24",235.0,0.25,0.35,0.30,-0.10,25,2)]

# ─── Ledger snapshots ─────────────────────────────────────────────────────────
def ledger_snapshot_roll_ready() -> CampaignLedgerSnapshot:
    return CampaignLedgerSnapshot(campaign_id="cmp_tsla_001",campaign_family="DEEP_ITM_CAMPAIGN",
        entry_family="DEEP_ITM_CALENDAR_ENTRY",opening_debit=8.0,opening_credit=0.0,
        realized_credit_collected=4.7,realized_close_cost=1.0,repair_debit_paid=0.0,
        net_campaign_basis=4.3,campaign_recovered_pct=46.25,campaign_cycle_count=2,
        campaign_realized_pnl=-4.3,current_structure="DEEP_ITM_CALENDAR",current_side="PUT")

def ledger_snapshot_bank_reduce() -> CampaignLedgerSnapshot:
    return CampaignLedgerSnapshot(campaign_id="cmp_tsla_002",campaign_family="DEEP_ITM_CAMPAIGN",
        entry_family="DEEP_ITM_CALENDAR_ENTRY",opening_debit=8.0,opening_credit=0.0,
        realized_credit_collected=8.0,realized_close_cost=0.3,repair_debit_paid=0.0,
        net_campaign_basis=0.3,campaign_recovered_pct=96.25,campaign_cycle_count=4,
        campaign_realized_pnl=-0.3,current_structure="DEEP_ITM_DIAGONAL",current_side="PUT")

# ─── State decisions ──────────────────────────────────────────────────────────
def state_decision_roll_ready() -> CampaignStateDecision:
    return CampaignStateDecision(campaign_state="ROLL_READY",campaign_action="ROLL",
        campaign_urgency=75,campaign_reason="Harvest threshold and continuation quality support a same-side net-credit roll.",
        state_score=73.0)

# ─── Lifecycle decisions ──────────────────────────────────────────────────────
def lifecycle_decision_roll_ready() -> CampaignLifecycleDecision:
    return CampaignLifecycleDecision(campaign_id="cmp_tsla_001",campaign_family="DEEP_ITM_CAMPAIGN",
        entry_family="DEEP_ITM_CALENDAR_ENTRY",campaign_state="ROLL_READY",campaign_action="ROLL",
        campaign_urgency=75,campaign_reason="Harvest threshold and continuation quality support a same-side net-credit roll.",
        state_score=73.0,selected_transition_type="ROLL_SAME_SIDE",selected_transition_approved=True,
        selected_transition_reason="Approved same-side roll candidate.",
        roll_output={"approved":True,"reason":"Approved same-side roll candidate.","roll_credit_est":0.7,
                     "future_roll_score":76.0,"proposed_short_strike":240.0,"proposed_short_expiry":"2026-04-17"},
        defense_output=None,
        flip_output={"flip_candidate":True,"approved":False,
                     "reason":"Same-side continuation remains clearly superior.",
                     "flip_to_side":"CALL","flip_credit_est":0.85,"flip_quality_score":72.0},
        collapse_output=None,
        summary="Campaign cmp_tsla_001 | Entry=DEEP_ITM_CALENDAR_ENTRY | State=ROLL_READY | Action=ROLL | SelectedTransition=ROLL_SAME_SIDE")

# ─── Ranked paths ─────────────────────────────────────────────────────────────
def ranked_paths_roll_then_flip() -> list[RankedPath]:
    return [
        RankedPath(path_code="ROLL_SAME_SIDE",path_total_score=84.0,
            campaign_recovery_score=72.0,future_roll_score=80.0,flip_quality_score=0.0,
            collapse_quality_score=0.0,campaign_complexity_score=62.0,execution_quality_score=82.0,
            regime_alignment_score=85.0,urgency_score=75.0,mandate_fit_score=90.0,
            simplicity_score=38.0,capital_efficiency_score=79.0,review_pressure_score=45.0,
            projected_credit=0.70,projected_debit=0.0,projected_basis_after_action=3.60,
            approved=True,reason="Approved same-side roll candidate.",
            tradeoff_note="Best for continuing basis recovery, but depends on ongoing roll continuity and execution quality.",
            details={"proposed_short_strike":240.0,"proposed_short_expiry":"2026-04-17",
                     "strike_improvement_score":82.0,"expected_move_clearance":0.95,"liquidity_score":82.0}),
        RankedPath(path_code="FLIP_SELECTIVELY",path_total_score=71.5,
            campaign_recovery_score=68.0,future_roll_score=62.0,flip_quality_score=76.0,
            collapse_quality_score=0.0,campaign_complexity_score=62.0,execution_quality_score=75.0,
            regime_alignment_score=78.0,urgency_score=55.0,mandate_fit_score=72.0,
            simplicity_score=50.0,capital_efficiency_score=73.0,review_pressure_score=60.0,
            projected_credit=0.85,projected_debit=0.0,projected_basis_after_action=3.45,
            approved=False,reason="Same-side continuation remains clearly superior.",
            tradeoff_note="May exploit skew and directional shift, but only when same-side continuation is not dominant.",
            details={"flip_to_side":"CALL"}),
    ]

# ─── Queue context ────────────────────────────────────────────────────────────
def queue_context_roll_ready() -> CampaignQueueContext:
    return CampaignQueueContext(environment="LIVE",symbol="TSLA",position_id="pos_001",
        campaign_id="cmp_tsla_001",campaign_family="DEEP_ITM_CAMPAIGN",
        entry_family="DEEP_ITM_CALENDAR_ENTRY",current_structure="DEEP_ITM_CALENDAR",
        current_side="PUT",short_strike=245.0,long_strike=270.0,short_expiry="2026-04-10",
        long_expiry="2026-05-15",short_dte=6,long_dte=35,current_profit_percent=42.0,
        distance_to_strike=12.0,expected_move=12.0,execution_surface_score=82.0,timing_score=81.0,
        regime_alignment_score=85.0,campaign_complexity_score=62.0,deployment_label="REDUCED",
        risk_envelope="DEFENSIVE",maturity_level="STABLE")

# ─── Workspace input ──────────────────────────────────────────────────────────
def workspace_input_roll_ready() -> CampaignWorkspaceInput:
    return CampaignWorkspaceInput(environment="LIVE",symbol="TSLA",position_id="pos_001",
        campaign_id="cmp_tsla_001",campaign_family="DEEP_ITM_CAMPAIGN",
        entry_family="DEEP_ITM_CALENDAR_ENTRY",current_structure="DEEP_ITM_CALENDAR",
        current_side="PUT",short_strike=245.0,long_strike=270.0,short_expiry="2026-04-10",
        long_expiry="2026-05-15",short_dte=6,long_dte=35,current_profit_percent=42.0,
        execution_surface_score=82.0,timing_score=81.0,regime_alignment_score=85.0,
        linked_review_ids=["rev_001"],knowledge_context_summaries=["TSLA neutral time-spread campaign active."],
        primary_rationale="Roll-ready campaign with strong same-side continuity.")

# ─── Ticket input ─────────────────────────────────────────────────────────────
def ticket_input_roll_ready() -> CampaignTransitionTicketInput:
    selected={"path_code":"ROLL_SAME_SIDE","approved":True,"projected_credit":0.70,
              "projected_debit":0.0,"projected_basis_after_action":3.60,"future_roll_score":80.0,
              "flip_quality_score":0.0,"collapse_quality_score":0.0,"path_total_score":84.0,
              "reason":"Approved same-side roll candidate.",
              "tradeoff_note":"Best for continuing basis recovery.",
              "details":{"proposed_short_strike":240.0,"proposed_short_expiry":"2026-04-17",
                         "strike_improvement_score":82.0,"expected_move_clearance":0.95,"liquidity_score":82.0}}
    alt={"path_code":"FLIP_SELECTIVELY","path_total_score":71.5}
    return CampaignTransitionTicketInput(environment="LIVE",symbol="TSLA",position_id="pos_001",
        campaign_id="cmp_tsla_001",campaign_family="DEEP_ITM_CAMPAIGN",
        entry_family="DEEP_ITM_CALENDAR_ENTRY",current_structure="DEEP_ITM_CALENDAR",
        current_side="PUT",campaign_state="ROLL_READY",campaign_action="ROLL",campaign_urgency=75,
        campaign_reason="Harvest threshold and continuation quality support a same-side net-credit roll.",
        opening_debit=8.0,opening_credit=0.0,realized_credit_collected=4.7,realized_close_cost=1.0,
        repair_debit_paid=0.0,net_campaign_basis=4.3,campaign_recovered_pct=46.25,
        campaign_cycle_count=2,campaign_realized_pnl=-4.3,selected_path=selected,alternative_path=alt,
        deployment_label="REDUCED",risk_envelope="DEFENSIVE",maturity_level="STABLE",
        linked_review_ids=["rev_001"],knowledge_context_summaries=["TSLA neutral time-spread campaign active."],
        primary_rationale="Roll-ready campaign with strong same-side continuity.")
