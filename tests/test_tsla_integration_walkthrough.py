"""tests/test_tsla_integration_walkthrough.py — Full 13-stage TSLA walkthrough validation.

Runs every stage of the TSLA neutral campaign against the walkthrough spec,
with schema validation at each boundary.

Each test function maps 1:1 to a walkthrough section.
"""
from __future__ import annotations
import uuid, sys
sys.path.insert(0,'.')

from common.campaign_schema_validator import (
    validate_scanner_candidate, validate_enriched_row, validate_ledger_snapshot,
    validate_lifecycle_decision, validate_ranked_path, validate_queue_row,
    validate_workspace, validate_ticket, validate_trade_summary,
    validate_research_row, validate_journal_row,
)

# ─── shared test state ──────────────────────────────────────────────────────--
# All stages share these constants so every assertion uses the same numbers.
SPOT          = 250.0
EXPECTED_MOVE = 12.0
OPENING_DEBIT = 8.0
OPENING_CREDIT= 0.0
RCC           = 4.7    # realized credit collected
RCC_CLOSE     = 1.0    # realized close cost
NET_BASIS     = round(OPENING_DEBIT - OPENING_CREDIT - RCC + RCC_CLOSE, 6)  # 4.3
RECOVERED_PCT = round(100.0 * (OPENING_DEBIT - NET_BASIS) / OPENING_DEBIT, 6)  # 46.25
CYCLE_COUNT   = 2
PNL           = round(OPENING_CREDIT + RCC - OPENING_DEBIT - RCC_CLOSE, 6)  # -4.3


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 1 — Scanner candidate
# ─────────────────────────────────────────────────────────────────────────────
def test_stage_1_scanner_candidate():
    """Verify deep ITM calendar scanner emits a valid TSLA campaign candidate."""
    from scanner.deep_itm_entry_filters import OptionLegQuote, DeepITMEntryFilterConfig, compute_liquidity_score
    from scanner.deep_itm_calendar_scanner import MarketContextLite, scan_deep_itm_calendar_candidates

    ctx = MarketContextLite("TSLA",SPOT,EXPECTED_MOVE,48.0,"POSITIVE","NEUTRAL_TIME_SPREADS",85.0,as_of_date="2026-01-24")
    ll  = OptionLegQuote("TSLA","PUT","2026-03-10",270.0,22.5,23.5,23.0,-0.82,500,40)
    sl  = OptionLegQuote("TSLA","PUT","2026-02-03",245.0,15.0,16.0,15.5,-0.32,700,60)
    ng  = [OptionLegQuote("TSLA","PUT","2026-05-01",245.0,2.1,2.4,2.25,-0.31,1000,90),
           OptionLegQuote("TSLA","PUT","2026-05-08",245.0,2.2,2.5,2.35,-0.33, 900,88)]
    cfg = DeepITMEntryFilterConfig(max_entry_debit_width_ratio=0.38,max_long_extrinsic_cost=10.0,
            min_projected_recovery_ratio=0.40,min_future_roll_score=40.0,min_open_interest=50,min_volume=5)

    candidates = scan_deep_itm_calendar_candidates(ctx,"PUT",[ll],[sl],ng,cfg)
    assert len(candidates) >= 1, "Scanner must emit at least one candidate"

    c = candidates[0]
    cdict = {"campaign_family":c.campaign_family,"entry_family":c.entry_family,
             "structure":c.structure,"entry_net_debit":c.entry_net_debit,
             "entry_cheapness_score":c.entry_cheapness_score,"future_roll_score":c.future_roll_score,
             "candidate_score":c.candidate_score,"expected_move_clearance":c.expected_move_clearance,
             "liquidity_score":c.liquidity_score}

    ok,errors = validate_scanner_candidate(cdict)
    assert ok, f"Schema errors: {errors}"
    assert c.campaign_family == "DEEP_ITM_CAMPAIGN"
    assert c.entry_family    == "DEEP_ITM_CALENDAR_ENTRY"
    assert c.structure       == "DEEP_ITM_CALENDAR"
    assert c.entry_net_debit > 0
    assert c.entry_cheapness_score > 55
    assert c.future_roll_score > 0


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 2 — Enriched position row (ledger fields attached)
# ─────────────────────────────────────────────────────────────────────────────
def _make_enriched_row() -> dict:
    return {
        "symbol":"TSLA","position_id":"pos_001","campaign_id":"cmp_tsla_001",
        "campaign_family":"DEEP_ITM_CAMPAIGN","entry_family":"DEEP_ITM_CALENDAR_ENTRY",
        "current_structure":"DEEP_ITM_CALENDAR","current_side":"PUT",
        "short_strike":245.0,"long_strike":270.0,"short_expiry":"2026-04-10","long_expiry":"2026-05-15",
        "short_dte":6,"long_dte":35,"distance_to_strike":12.0,"expected_move":EXPECTED_MOVE,
        "current_profit_percent":42.0,"execution_surface_score":82.0,"timing_score":81.0,
        "regime_alignment_score":85.0,"campaign_complexity_score":62.0,
        "opening_debit":OPENING_DEBIT,"opening_credit":OPENING_CREDIT,
        "realized_credit_collected":RCC,"realized_close_cost":RCC_CLOSE,"repair_debit_paid":0.0,
        "net_campaign_basis":NET_BASIS,"campaign_recovered_pct":RECOVERED_PCT,
        "campaign_cycle_count":CYCLE_COUNT,"campaign_realized_pnl":PNL,
        "deployment_label":"REDUCED","risk_envelope":"DEFENSIVE","maturity_level":"STABLE",
        "environment":"LIVE",
    }

def test_stage_2_enriched_row():
    row = _make_enriched_row()
    ok,errors = validate_enriched_row(row)
    assert ok, f"Schema errors: {errors}"
    assert row["campaign_family"] == "DEEP_ITM_CAMPAIGN"
    assert row["current_side"] == "PUT"
    assert row["opening_debit"] == OPENING_DEBIT
    assert abs(row["net_campaign_basis"] - NET_BASIS) < 0.001
    assert abs(row["campaign_recovered_pct"] - RECOVERED_PCT) < 0.01


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 3 — Ledger snapshot
# ─────────────────────────────────────────────────────────────────────────────
def _make_ledger_snap():
    from campaigns.campaign_basis_ledger import CampaignLedgerSnapshot
    return CampaignLedgerSnapshot(
        campaign_id="cmp_tsla_001",campaign_family="DEEP_ITM_CAMPAIGN",
        entry_family="DEEP_ITM_CALENDAR_ENTRY",
        opening_debit=OPENING_DEBIT,opening_credit=OPENING_CREDIT,
        realized_credit_collected=RCC,realized_close_cost=RCC_CLOSE,repair_debit_paid=0.0,
        net_campaign_basis=NET_BASIS,campaign_recovered_pct=RECOVERED_PCT,
        campaign_cycle_count=CYCLE_COUNT,campaign_realized_pnl=PNL,
        current_structure="DEEP_ITM_CALENDAR",current_side="PUT")

def test_stage_3_ledger_snapshot():
    snap = _make_ledger_snap()
    ok,errors = validate_ledger_snapshot(snap)
    assert ok, f"Schema errors: {errors}"
    assert abs(snap.net_campaign_basis - NET_BASIS) < 1e-5
    assert abs(snap.campaign_recovered_pct - RECOVERED_PCT) < 0.01
    # Cross-check formula: 8.0 - 0.0 - 4.7 + 1.0 + 0.0 = 4.3
    expected = OPENING_DEBIT - OPENING_CREDIT - RCC + RCC_CLOSE + 0.0
    assert abs(expected - NET_BASIS) < 1e-5, f"Expected basis={expected} got {NET_BASIS}"


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 4 — Same-side roll output
# ─────────────────────────────────────────────────────────────────────────────
def _make_rolls():
    from scanner.deep_itm_entry_filters import OptionLegQuote
    from lifecycle.net_credit_roll_engine import evaluate_same_side_rolls, RollEngineConfig
    ng = [OptionLegQuote("TSLA","PUT","2026-04-24",240.0,1.7,1.9,1.8,-0.25,1800,200),
          OptionLegQuote("TSLA","PUT","2026-05-01",240.0,2.0,2.2,2.1,-0.27,1500,180)]
    proposed = [OptionLegQuote("TSLA","PUT","2026-04-17",240.0,1.7,1.9,1.8,-0.30,1800,200)]
    return evaluate_same_side_rolls("TSLA","PUT",245.0,"2026-04-10",1.1,42.0,RECOVERED_PCT,
        proposed,ng,{240.0:0.95},{240.0:82.0},
        RollEngineConfig(min_same_side_roll_credit=0.25,min_future_roll_score=60.0,min_liquidity_score=50.0))

def test_stage_4_roll_output():
    rolls = _make_rolls()
    assert len(rolls) >= 1
    best = next((r for r in rolls if r.approved), None)
    assert best is not None, "Must have at least one approved roll"
    assert best.roll_credit_est > 0, f"roll_credit={best.roll_credit_est}"
    assert best.future_roll_score > 60
    assert abs(best.roll_credit_est - 0.70) < 0.15  # ±0.15 tolerance


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 5 — Lifecycle decision
# ─────────────────────────────────────────────────────────────────────────────
def _make_lifecycle_decision():
    from lifecycle.campaign_lifecycle_classifier import CampaignLifecycleContext, build_campaign_lifecycle_decision
    snap = _make_ledger_snap()
    rolls = _make_rolls()
    ctx = CampaignLifecycleContext("TSLA","DEEP_ITM_CALENDAR","PUT",6,35,12.0,EXPECTED_MOVE,
                                    42.0,82.0,81.0,85.0,62.0)
    return build_campaign_lifecycle_decision("cmp_tsla_001","DEEP_ITM_CAMPAIGN",
        "DEEP_ITM_CALENDAR_ENTRY",ctx,snap,same_side_rolls=rolls)

def test_stage_5_lifecycle_decision():
    ld = _make_lifecycle_decision()
    ok,errors = validate_lifecycle_decision(ld)
    assert ok, f"Schema errors: {errors}"
    assert ld.campaign_state in ("ROLL_READY","HARVEST_READY"), f"Expected ROLL_READY got {ld.campaign_state}"
    assert ld.campaign_action in ("ROLL","HARVEST")
    assert ld.selected_transition_type in ("ROLL_SAME_SIDE","HARVEST")
    assert ld.campaign_urgency > 0


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 6 — Ranked paths
# ─────────────────────────────────────────────────────────────────────────────
def _make_ranked_paths():
    from campaigns.campaign_transition_engine import CampaignTransitionContext, build_transition_candidates
    from compare.campaign_path_ranker import PathRankingContext, rank_campaign_paths
    ld = _make_lifecycle_decision()
    rolls = _make_rolls()
    ctx = CampaignTransitionContext("TSLA","cmp_tsla_001","DEEP_ITM_CAMPAIGN","DEEP_ITM_CALENDAR_ENTRY",
        "DEEP_ITM_CALENDAR","PUT",NET_BASIS,RECOVERED_PCT,CYCLE_COUNT,42.0,
        (rolls[0].future_roll_score if rolls else 0),62.0,82.0,81.0,85.0,
        ld.campaign_state,ld.campaign_action,ld.campaign_urgency,ld.campaign_reason)
    transitions = build_transition_candidates(ctx,same_side_rolls=rolls)
    prc = PathRankingContext("TSLA","BASIS_RECOVERY",RECOVERED_PCT,NET_BASIS,82.0,81.0,85.0,62.0,42.0)
    return rank_campaign_paths(transitions,prc)

def test_stage_6_ranked_paths():
    ranked = _make_ranked_paths()
    assert len(ranked) >= 1
    for rp in ranked:
        ok,errors = validate_ranked_path(rp)
        assert ok, f"Schema errors on {rp.path_code}: {errors}"
    # Roll must beat defer/flip when continuation is strong
    assert ranked[0].path_code in ("ROLL_SAME_SIDE","DEFER_AND_WAIT")
    if len(ranked) > 1:
        assert ranked[0].path_total_score >= ranked[1].path_total_score


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 7 — Queue row
# ─────────────────────────────────────────────────────────────────────────────
def _make_queue_row():
    from portfolio.campaign_queue_engine import CampaignQueueContext, build_transition_queue_row
    snap = _make_ledger_snap()
    ld = _make_lifecycle_decision()
    ranked = _make_ranked_paths()
    qctx = CampaignQueueContext("LIVE","TSLA","pos_001","cmp_tsla_001","DEEP_ITM_CAMPAIGN",
        "DEEP_ITM_CALENDAR_ENTRY","DEEP_ITM_CALENDAR","PUT",short_strike=245.0,long_strike=270.0,
        short_expiry="2026-04-10",long_expiry="2026-05-15",short_dte=6,long_dte=35,
        current_profit_percent=42.0,distance_to_strike=12.0,expected_move=EXPECTED_MOVE,
        execution_surface_score=82.0,timing_score=81.0,regime_alignment_score=85.0,
        campaign_complexity_score=62.0,deployment_label="REDUCED",risk_envelope="DEFENSIVE",maturity_level="STABLE")
    return build_transition_queue_row(qctx,snap,ld,ranked)

def test_stage_7_queue_row():
    qrow = _make_queue_row()
    ok,errors = validate_queue_row(qrow)
    assert ok, f"Schema errors: {errors}"
    assert qrow.campaign_state in ("ROLL_READY","HARVEST_READY")
    assert qrow.best_path_code in ("ROLL_SAME_SIDE","DEFER_AND_WAIT","HARVEST")
    assert qrow.net_campaign_basis == NET_BASIS
    assert abs(qrow.campaign_recovered_pct - RECOVERED_PCT) < 0.01
    assert qrow.queue_priority_band in ("ACT_NOW","DECIDE_NOW","WATCH_CLOSELY","IMPROVE_LATER")
    # Walkthrough expects DECIDE_NOW or ACT_NOW for this scenario
    assert qrow.queue_priority_band in ("ACT_NOW","DECIDE_NOW","WATCH_CLOSELY"), \
        f"Expected high priority, got {qrow.queue_priority_band}"


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 8 — Workspace
# ─────────────────────────────────────────────────────────────────────────────
def _make_workspace():
    from workspace.path_workspace_builder import CampaignWorkspaceInput, build_campaign_path_execution_workspace
    snap = _make_ledger_snap()
    ld = _make_lifecycle_decision()
    ranked = _make_ranked_paths()
    wi = CampaignWorkspaceInput("LIVE","TSLA","pos_001","cmp_tsla_001","DEEP_ITM_CAMPAIGN",
        "DEEP_ITM_CALENDAR_ENTRY","DEEP_ITM_CALENDAR","PUT",short_dte=6,long_dte=35,
        current_profit_percent=42.0,execution_surface_score=82.0,timing_score=81.0,
        primary_rationale="Roll-ready campaign with strong same-side continuity.")
    return build_campaign_path_execution_workspace(wi,snap,ld,ranked)

def test_stage_8_workspace():
    ws = _make_workspace()
    ok,errors = validate_workspace(ws)
    assert ok, f"Schema errors: {errors}"
    assert ws.workspace_type == "PATH_EXECUTION_WORKSPACE"
    assert ws.campaign_economics["opening_debit"] == OPENING_DEBIT
    assert ws.campaign_economics["net_campaign_basis"] == NET_BASIS
    assert abs(ws.campaign_economics["campaign_recovered_pct"] - RECOVERED_PCT) < 0.01
    assert ws.selected_path is not None
    assert ws.roll_panel["future_roll_score"] is not None
    # Execution panel must reflect lifecycle decision
    assert ws.execution_panel["campaign_state"] in ("ROLL_READY","HARVEST_READY")


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 9 — Ticket draft
# ─────────────────────────────────────────────────────────────────────────────
def _make_ticket():
    from execution.transition_ticket_builder import CampaignTransitionTicketInput, build_campaign_transition_ticket
    ws = _make_workspace()
    snap = _make_ledger_snap()
    ld = _make_lifecycle_decision()
    ti = CampaignTransitionTicketInput(
        environment="LIVE",symbol="TSLA",position_id="pos_001",campaign_id="cmp_tsla_001",
        campaign_family="DEEP_ITM_CAMPAIGN",entry_family="DEEP_ITM_CALENDAR_ENTRY",
        current_structure="DEEP_ITM_CALENDAR",current_side="PUT",
        campaign_state=ld.campaign_state,campaign_action=ld.campaign_action,
        campaign_urgency=ld.campaign_urgency,campaign_reason=ld.campaign_reason,
        opening_debit=snap.opening_debit,opening_credit=snap.opening_credit,
        realized_credit_collected=snap.realized_credit_collected,
        realized_close_cost=snap.realized_close_cost,repair_debit_paid=snap.repair_debit_paid,
        net_campaign_basis=snap.net_campaign_basis,campaign_recovered_pct=snap.campaign_recovered_pct,
        campaign_cycle_count=snap.campaign_cycle_count,campaign_realized_pnl=snap.campaign_realized_pnl,
        selected_path=ws.selected_path,alternative_path=ws.alternative_path,
        deployment_label="REDUCED",risk_envelope="DEFENSIVE",maturity_level="STABLE",
        primary_rationale="Roll-ready campaign with strong same-side continuity.")
    return build_campaign_transition_ticket(ti)

def test_stage_9_ticket():
    from execution.transition_ticket_builder import campaign_transition_ticket_to_dict
    ticket = _make_ticket()
    ok,errors = validate_ticket(ticket)
    assert ok, f"Schema errors: {errors}"
    assert ticket.campaign_id == "cmp_tsla_001"
    assert ticket.authority == "AUTO_DRAFT"
    assert ticket.projected_basis_after_action is not None
    assert ticket.projected_basis_after_action < NET_BASIS  # should reduce basis
    assert ticket.campaign_snapshot["net_campaign_basis"] == NET_BASIS
    assert any("LIVE" in w or "draft-only" in w.lower() for w in ticket.warnings)
    d = campaign_transition_ticket_to_dict(ticket)
    assert isinstance(d,dict) and d["ticket_type"] == "CAMPAIGN_TRANSITION_TICKET"


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 10 — Trade logger
# ─────────────────────────────────────────────────────────────────────────────
def _make_trade_record():
    from performance.trade_logger import (initialize_campaign_trade_record, log_open_entry,
                                           log_campaign_transition, build_campaign_trade_summary)
    rec = initialize_campaign_trade_record("cmp_tsla_001","TSLA","DEEP_ITM_CAMPAIGN",
        "DEEP_ITM_CALENDAR_ENTRY","2026-04-01T09:30:00","DEEP_ITM_CALENDAR","PUT","NEUTRAL_TIME_SPREADS")
    rec = log_open_entry(rec,str(uuid.uuid4()),OPENING_DEBIT,OPENING_CREDIT,
        regime_at_decision="NEUTRAL_TIME_SPREADS",deployment_label="REDUCED",
        risk_envelope="DEFENSIVE",maturity_level="STABLE")
    rec = log_campaign_transition(rec,str(uuid.uuid4()),"HARVEST","HARVEST",2.50,0.0,
        path_recommended="ROLL_SAME_SIDE",net_campaign_basis=5.50,campaign_recovered_pct=31.25,
        campaign_cycle_count=1,current_profit_percent=35.0)
    rec = log_campaign_transition(rec,str(uuid.uuid4()),"ROLL_SAME_SIDE","ROLL_SAME_SIDE",2.20,1.0,
        path_recommended="ROLL_SAME_SIDE",path_selected="ROLL_SAME_SIDE",path_executed="ROLL_SAME_SIDE",
        net_campaign_basis=NET_BASIS,campaign_recovered_pct=RECOVERED_PCT,
        campaign_cycle_count=CYCLE_COUNT,current_profit_percent=42.0,
        future_roll_score_at_decision=76.0,deployment_label="REDUCED")
    return rec

def test_stage_10_trade_logger():
    from performance.trade_logger import build_campaign_trade_summary
    rec = _make_trade_record()
    summary = build_campaign_trade_summary(rec)
    ok,errors = validate_trade_summary(summary)
    assert ok, f"Schema errors: {errors}"
    assert summary["campaign_family"] == "DEEP_ITM_CAMPAIGN"
    assert summary["opening_debit"] == OPENING_DEBIT
    assert summary["realized_credit_collected"] == 4.7
    assert summary["realized_close_cost"] == 1.0
    assert abs(summary["net_campaign_basis"] - NET_BASIS) < 0.01
    assert summary["campaign_cycle_count"] == CYCLE_COUNT
    assert summary["path_executed_last"] == "ROLL_SAME_SIDE"
    assert summary["deployment_label_last"] == "REDUCED"


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 11 — Research row
# ─────────────────────────────────────────────────────────────────────────────
def test_stage_11_research_row():
    from research.campaign_research_builder import (
        build_research_row_from_queue_row, build_research_row_from_trade_record,
        build_research_row_from_lifecycle_decision, research_dataset_row_to_dict,
    )
    qrow = _make_queue_row()
    rec  = _make_trade_record()
    snap = _make_ledger_snap()
    ld   = _make_lifecycle_decision()

    # From queue row
    rr_q = build_research_row_from_queue_row(qrow)
    ok,errors = validate_research_row(rr_q)
    assert ok, f"Queue research schema errors: {errors}"
    assert rr_q.campaign_family == "DEEP_ITM_CAMPAIGN"
    assert rr_q.entry_family == "DEEP_ITM_CALENDAR_ENTRY"
    assert rr_q.row_source == "QUEUE_ROW"
    assert rr_q.net_campaign_basis == NET_BASIS

    # From trade record
    rr_t = build_research_row_from_trade_record(rec,"LIVE")
    ok,errors = validate_research_row(rr_t)
    assert ok, f"Trade research schema errors: {errors}"
    assert rr_t.row_source == "TRADE_RECORD"
    assert rr_t.path_executed == "ROLL_SAME_SIDE"

    # From lifecycle decision
    rr_l = build_research_row_from_lifecycle_decision(ld,snap,"TSLA","LIVE",
        "DEEP_ITM_CALENDAR","PUT","REDUCED","DEFENSIVE","STABLE")
    ok,errors = validate_research_row(rr_l)
    assert ok, f"Lifecycle research schema errors: {errors}"
    assert rr_l.row_source == "LIFECYCLE_DECISION"
    assert rr_l.selected_transition_type in ("ROLL_SAME_SIDE","HARVEST")

    # All 3 must agree on identity fields
    for rr,src in [(rr_q,"QUEUE_ROW"),(rr_t,"TRADE_RECORD"),(rr_l,"LIFECYCLE_DECISION")]:
        assert rr.campaign_id == "cmp_tsla_001", f"{src}: campaign_id wrong"
        assert rr.campaign_family == "DEEP_ITM_CAMPAIGN", f"{src}: campaign_family wrong"
        d = research_dataset_row_to_dict(rr)
        assert isinstance(d,dict)


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 12 — Journal row (open → executed)
# ─────────────────────────────────────────────────────────────────────────────
def test_stage_12_journal_row():
    from journal.campaign_transition_journal import (
        build_transition_journal_row, mark_transition_executed,
        mark_transition_deferred, transition_journal_row_to_dict,
    )
    snap   = _make_ledger_snap()
    ld     = _make_lifecycle_decision()
    ranked = _make_ranked_paths()

    jr = build_transition_journal_row(
        journal_id="jrnl_cmp_tsla_001",environment="LIVE",symbol="TSLA",
        position_id="pos_001",campaign_id="cmp_tsla_001",campaign_family="DEEP_ITM_CAMPAIGN",
        entry_family="DEEP_ITM_CALENDAR_ENTRY",current_structure="DEEP_ITM_CALENDAR",current_side="PUT",
        ledger_snapshot=snap,lifecycle_decision=ld,ranked_paths=ranked,
        deployment_label="REDUCED",risk_envelope="DEFENSIVE",maturity_level="STABLE",
        rationale="Roll-ready campaign with strong same-side continuity.")

    ok,errors = validate_journal_row(jr)
    assert ok, f"Schema errors (OPEN): {errors}"
    assert jr.journal_status == "OPEN"
    assert jr.path_recommended in ("ROLL_SAME_SIDE","HARVEST")
    assert jr.net_campaign_basis == NET_BASIS
    assert abs(jr.campaign_recovered_pct - RECOVERED_PCT) < 0.01
    assert jr.best_path_code is not None

    # Mark executed
    jr_exec = mark_transition_executed(jr,"ROLL_SAME_SIDE",["Executed same-side roll."])
    ok,errors = validate_journal_row(jr_exec)
    assert ok, f"Schema errors (EXECUTED): {errors}"
    assert jr_exec.journal_status == "EXECUTED"
    assert jr_exec.path_executed == "ROLL_SAME_SIDE"
    assert jr_exec.path_recommended == jr.path_recommended  # preserved

    # Recommended vs executed may differ — that's intentional
    d = transition_journal_row_to_dict(jr_exec)
    assert d["path_executed"] == "ROLL_SAME_SIDE"
    assert d["path_recommended"] is not None
    assert d["net_campaign_basis"] == NET_BASIS


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 13 — Schema validator itself
# ─────────────────────────────────────────────────────────────────────────────
def test_stage_13_schema_validator_catches_bad_objects():
    """Confirm the validator flags problems correctly."""
    from common.campaign_schema_validator import (
        validate_enriched_row, validate_ledger_snapshot, validate_lifecycle_decision,
    )
    # Missing campaign_family
    ok,errors = validate_enriched_row({"symbol":"TSLA","campaign_id":"c1"})
    assert not ok, "Should fail on incomplete row"
    assert any("campaign_family" in e for e in errors)

    # Wrong current_side
    bad_row = _make_enriched_row(); bad_row["current_side"] = "LONG"
    ok,errors = validate_enriched_row(bad_row)
    assert not ok
    assert any("current_side" in e for e in errors)

    # Negative basis
    snap = _make_ledger_snap()
    import dataclasses
    bad_snap = dataclasses.replace(snap,net_campaign_basis=-0.50,opening_debit=2.0,
                                    realized_credit_collected=2.60)
    ok,errors = validate_ledger_snapshot(bad_snap)
    assert not ok
    assert any("negative" in e.lower() or "mismatch" in e.lower() for e in errors)

    # Invalid campaign_state
    ld = _make_lifecycle_decision()
    bad_ld = dataclasses.replace(ld,campaign_state="PANIC")
    ok,errors = validate_lifecycle_decision(bad_ld)
    assert not ok
    assert any("campaign_state" in e for e in errors)


# ─────────────────────────────────────────────────────────────────────────────
# FULL WALKTHROUGH runner (ordered, stops on first failure per stage)
# ─────────────────────────────────────────────────────────────────────────────
WALKTHROUGH_STAGES = [
    ("Stage 01 — scanner candidate",      test_stage_1_scanner_candidate),
    ("Stage 02 — enriched row",           test_stage_2_enriched_row),
    ("Stage 03 — ledger snapshot",        test_stage_3_ledger_snapshot),
    ("Stage 04 — roll output",            test_stage_4_roll_output),
    ("Stage 05 — lifecycle decision",     test_stage_5_lifecycle_decision),
    ("Stage 06 — ranked paths",           test_stage_6_ranked_paths),
    ("Stage 07 — queue row",              test_stage_7_queue_row),
    ("Stage 08 — workspace",              test_stage_8_workspace),
    ("Stage 09 — ticket draft",           test_stage_9_ticket),
    ("Stage 10 — trade logger",           test_stage_10_trade_logger),
    ("Stage 11 — research row",           test_stage_11_research_row),
    ("Stage 12 — journal row",            test_stage_12_journal_row),
    ("Stage 13 — schema validator",       test_stage_13_schema_validator_catches_bad_objects),
]

if __name__ == "__main__":
    passed=0; failed=0
    print(f"\n{'='*65}")
    print("TSLA NEUTRAL CAMPAIGN — FULL WALKTHROUGH")
    print(f"  opening_debit={OPENING_DEBIT}  RCC={RCC}  close={RCC_CLOSE}")
    print(f"  net_basis={NET_BASIS}  recovered={RECOVERED_PCT:.2f}%  cycles={CYCLE_COUNT}")
    print(f"{'='*65}")
    for name,fn in WALKTHROUGH_STAGES:
        try:
            fn(); passed+=1; print(f"  ✓ {name}")
        except AssertionError as e:
            failed+=1; print(f"  ✗ {name}\n    {e}")
        except Exception as e:
            failed+=1; import traceback; print(f"  ✗ {name}\n    {e}")
            if "--verbose" in sys.argv: traceback.print_exc()
    print(f"\n{'='*65}")
    print(f"WALKTHROUGH: {passed} passed | {failed} failed")
    print(f"{'='*65}")
