"""tests/test_live_validation_harness.py — Harness correctness with fixture inputs."""
from validation.live_validation_harness import run_live_validation_batch
from tests.fixtures.deep_itm_campaign_fixtures import (
    tsla_neutral_context, long_put_deep_itm_valid, short_put_valid,
    next_generation_short_puts_good, queue_context_roll_ready, ledger_snapshot_roll_ready,
)

def _tracked_tsla():
    q=queue_context_roll_ready(); snap=ledger_snapshot_roll_ready()
    ng=next_generation_short_puts_good()
    return {"symbol":q.symbol,"position_id":q.position_id,"campaign_id":q.campaign_id,
            "campaign_family":q.campaign_family,"entry_family":q.entry_family,
            "current_structure":q.current_structure,"current_side":q.current_side,
            "short_strike":q.short_strike,"long_strike":q.long_strike,
            "short_expiry":q.short_expiry,"long_expiry":q.long_expiry,
            "short_dte":q.short_dte,"long_dte":q.long_dte,
            "distance_to_strike":q.distance_to_strike,"expected_move":q.expected_move,
            "current_profit_percent":q.current_profit_percent,
            "execution_surface_score":q.execution_surface_score,"timing_score":q.timing_score,
            "regime_alignment_score":q.regime_alignment_score,"campaign_complexity_score":q.campaign_complexity_score,
            "opening_debit":snap.opening_debit,"opening_credit":snap.opening_credit,
            "realized_credit_collected":snap.realized_credit_collected,"realized_close_cost":snap.realized_close_cost,
            "repair_debit_paid":snap.repair_debit_paid,"net_campaign_basis":snap.net_campaign_basis,
            "campaign_recovered_pct":snap.campaign_recovered_pct,"campaign_cycle_count":snap.campaign_cycle_count,
            "campaign_realized_pnl":snap.campaign_realized_pnl,
            "deployment_label":q.deployment_label,"risk_envelope":q.risk_envelope,"maturity_level":q.maturity_level,
            "current_short_close_cost":1.1,"proposed_same_side_shorts":ng,"next_generation_shorts":ng,
            "expected_move_clearance_by_strike":{240.0:0.95,245.0:0.75},
            "liquidity_score_by_strike":{240.0:82.0,245.0:80.0},
            "linked_review_ids":["rev_001"],"knowledge_context_summaries":["TSLA campaign active."],
            "campaign_reason":"Roll-ready campaign."}

def test_live_validation_batch_runs():
    ctx=tsla_neutral_context()
    results=run_live_validation_batch(
        environment="LIVE",
        context_by_symbol={"TSLA":ctx,"SPY":ctx,"QQQ":ctx},
        long_leg_quotes_by_symbol={"TSLA":[long_put_deep_itm_valid()],"SPY":[],"QQQ":[]},
        short_leg_quotes_by_symbol={"TSLA":[short_put_valid()],"SPY":[],"QQQ":[]},
        next_generation_shorts_by_symbol={"TSLA":next_generation_short_puts_good(),"SPY":[],"QQQ":[]},
        tracked_campaign_rows_by_symbol={})
    assert len(results)==3
    assert results[0]["symbol"]=="TSLA"
    assert results[1]["symbol"]=="SPY"
    assert results[2]["symbol"]=="QQQ"

def test_tsla_candidate_found():
    """Uses expiries calibrated to as_of_date=2026-01-24 so DTE falls in valid range."""
    from scanner.deep_itm_entry_filters import OptionLegQuote
    ctx=tsla_neutral_context()  # as_of_date="2026-01-24"
    # long: 2026-03-10 = 45 DTE from 2026-01-24 ✓  short: 2026-02-03 = 10 DTE ✓
    ll=OptionLegQuote("TSLA","PUT","2026-03-10",270.0,22.5,23.5,23.0,-0.82,500,40)
    sl=OptionLegQuote("TSLA","PUT","2026-02-03",245.0,15.0,16.0,15.5,-0.32,700,60)
    ng=next_generation_short_puts_good()
    results=run_live_validation_batch(environment="LIVE",
        context_by_symbol={"TSLA":ctx,"SPY":ctx,"QQQ":ctx},
        long_leg_quotes_by_symbol={"TSLA":[ll],"SPY":[],"QQQ":[]},
        short_leg_quotes_by_symbol={"TSLA":[sl],"SPY":[],"QQQ":[]},
        next_generation_shorts_by_symbol={"TSLA":ng,"SPY":[],"QQQ":[]})
    tsla=[r for r in results if r["symbol"]=="TSLA"][0]
    assert tsla["candidate_found"], f"warnings={tsla['warnings']}"
    assert tsla["campaign_family"]=="DEEP_ITM_CAMPAIGN"

def test_tsla_tracked_campaign_full_pipeline():
    ctx=tsla_neutral_context()
    results=run_live_validation_batch(environment="LIVE",
        context_by_symbol={"TSLA":ctx,"SPY":ctx,"QQQ":ctx},
        long_leg_quotes_by_symbol={"TSLA":[long_put_deep_itm_valid()],"SPY":[],"QQQ":[]},
        short_leg_quotes_by_symbol={"TSLA":[short_put_valid()],"SPY":[],"QQQ":[]},
        next_generation_shorts_by_symbol={"TSLA":next_generation_short_puts_good(),"SPY":[],"QQQ":[]},
        tracked_campaign_rows_by_symbol={"TSLA":_tracked_tsla()})
    tsla=[r for r in results if r["symbol"]=="TSLA"][0]
    # Should run full pipeline
    assert tsla["campaign_id"]=="cmp_tsla_001"
    assert tsla["campaign_state"] in ("ROLL_READY","HARVEST_READY")
    assert tsla["best_path_code"] in ("ROLL_SAME_SIDE","DEFER_AND_WAIT","HARVEST")
    assert tsla["queue_priority_band"] in ("ACT_NOW","DECIDE_NOW","WATCH_CLOSELY","IMPROVE_LATER")
    assert tsla["ticket_ready"] is True
    assert tsla["net_campaign_basis"]==4.3
    assert len(tsla["warnings"])==0

def test_spy_qqq_graceful_no_campaign():
    ctx=tsla_neutral_context()
    results=run_live_validation_batch(environment="LIVE",
        context_by_symbol={"TSLA":ctx,"SPY":ctx,"QQQ":ctx},
        long_leg_quotes_by_symbol={"TSLA":[],"SPY":[],"QQQ":[]},
        short_leg_quotes_by_symbol={"TSLA":[],"SPY":[],"QQQ":[]},
        next_generation_shorts_by_symbol={"TSLA":[],"SPY":[],"QQQ":[]})
    for r in results:
        assert "symbol" in r
        assert isinstance(r["warnings"],list)
        assert r["ticket_ready"] is False

def test_missing_context_returns_clean_result():
    results=run_live_validation_batch(environment="LIVE",
        context_by_symbol={},  # no context for any symbol
        long_leg_quotes_by_symbol={},short_leg_quotes_by_symbol={},
        next_generation_shorts_by_symbol={})
    assert len(results)==3
    for r in results:
        assert "No market context" in r["warnings"][0]
