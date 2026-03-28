"""validation/run_live_validation.py — Repeatable daily validation entry point."""
from __future__ import annotations
import json, sys
from pathlib import Path
from datetime import datetime
from typing import Any

sys.path.insert(0,'.')
from validation.live_validation_harness import run_live_validation_batch
from validation.live_validation_reporter import build_live_validation_report, render_live_validation_report_text

def _utc_ts() -> str: return datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
def _outdir() -> Path: p=Path("validation_artifacts"); p.mkdir(parents=True,exist_ok=True); return p
def _write_json(name,payload): p=_outdir()/name; p.write_text(json.dumps(payload,indent=2,default=str)); return p
def _write_text(name,text): p=_outdir()/name; p.write_text(text); return p

# ── Stub loaders (replace with real app loaders) ──────────────────────────────
def load_context_by_symbol() -> dict[str,Any]:
    from tests.fixtures.deep_itm_campaign_fixtures import tsla_neutral_context
    ctx=tsla_neutral_context()
    return {"TSLA":ctx,"SPY":ctx,"QQQ":ctx}

def load_long_leg_quotes_by_symbol() -> dict[str,list[Any]]:
    from tests.fixtures.deep_itm_campaign_fixtures import long_put_deep_itm_valid
    return {"TSLA":[long_put_deep_itm_valid()],"SPY":[],"QQQ":[]}

def load_short_leg_quotes_by_symbol() -> dict[str,list[Any]]:
    from tests.fixtures.deep_itm_campaign_fixtures import short_put_valid
    return {"TSLA":[short_put_valid()],"SPY":[],"QQQ":[]}

def load_next_generation_shorts_by_symbol() -> dict[str,list[Any]]:
    from tests.fixtures.deep_itm_campaign_fixtures import next_generation_short_puts_good
    return {"TSLA":next_generation_short_puts_good(),"SPY":[],"QQQ":[]}

def load_tracked_campaign_rows_by_symbol() -> dict[str,dict[str,Any]]:
    from tests.fixtures.deep_itm_campaign_fixtures import queue_context_roll_ready, ledger_snapshot_roll_ready
    q=queue_context_roll_ready(); snap=ledger_snapshot_roll_ready()
    ng=load_next_generation_shorts_by_symbol()["TSLA"]
    return {"TSLA":{
        "symbol":q.symbol,"position_id":q.position_id,"campaign_id":q.campaign_id,
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
        "linked_review_ids":["rev_001"],"knowledge_context_summaries":["TSLA neutral campaign active."],
        "campaign_reason":"Harvest threshold and continuation quality support a same-side net-credit roll.",
    }}

def main() -> int:
    results=run_live_validation_batch(
        environment="LIVE",context_by_symbol=load_context_by_symbol(),
        long_leg_quotes_by_symbol=load_long_leg_quotes_by_symbol(),
        short_leg_quotes_by_symbol=load_short_leg_quotes_by_symbol(),
        next_generation_shorts_by_symbol=load_next_generation_shorts_by_symbol(),
        tracked_campaign_rows_by_symbol=load_tracked_campaign_rows_by_symbol())
    report=build_live_validation_report(results)
    text=render_live_validation_report_text(results)
    print(text)
    stamp=_utc_ts()
    jpath=_write_json(f"live_validation_{stamp}.json",report)
    tpath=_write_text(f"live_validation_{stamp}.txt",text)
    print(f"\nWrote JSON report: {jpath}")
    print(f"Wrote text report: {tpath}")
    return 0

if __name__=="__main__": raise SystemExit(main())
