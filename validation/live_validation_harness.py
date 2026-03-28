"""validation/live_validation_harness.py — Full pipeline validation for TSLA/SPY/QQQ."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from scanner.deep_itm_entry_filters import DeepITMEntryFilterConfig
from scanner.deep_itm_calendar_scanner import scan_deep_itm_calendar_candidates
from campaigns.campaign_basis_ledger import CampaignLedgerSnapshot
from lifecycle.net_credit_roll_engine import RollEngineConfig, evaluate_same_side_rolls
from lifecycle.campaign_lifecycle_classifier import (CampaignLifecycleContext, build_campaign_lifecycle_decision)
from campaigns.campaign_transition_engine import (CampaignTransitionContext, build_transition_candidates)
from compare.campaign_path_ranker import PathRankingContext, rank_campaign_paths
from portfolio.campaign_queue_engine import (CampaignQueueContext, build_transition_queue_row)
from workspace.path_workspace_builder import (CampaignWorkspaceInput, build_campaign_path_execution_workspace)
from execution.transition_ticket_builder import (CampaignTransitionTicketInput, build_campaign_transition_ticket)
from common.campaign_schema_validator import validate_campaign_pipeline_stage

SYMBOLS = ["TSLA","SPY","QQQ"]

def _utcnow() -> str:
    return datetime.utcnow().isoformat()

def validate_symbol_live(symbol: str, environment: str, context: Any,
                          long_leg_quotes: list[Any], short_leg_quotes: list[Any],
                          next_generation_shorts: list[Any],
                          tracked_campaign_row: dict[str,Any]|None=None) -> dict[str,Any]:
    result: dict[str,Any] = {
        "symbol":symbol,"timestamp_utc":_utcnow(),"environment":environment,
        "regime_environment":getattr(context,"environment",None),
        "regime_alignment_score":getattr(context,"regime_alignment_score",None),
        "campaign_family":None,"entry_family":None,"current_structure":None,"current_side":None,
        "candidate_found":False,"candidate_score":None,"entry_cheapness_score":None,
        "projected_recovery_ratio":None,"future_roll_score":None,
        "campaign_id":None,"net_campaign_basis":None,"campaign_recovered_pct":None,"campaign_cycle_count":None,
        "campaign_state":None,"campaign_action":None,"selected_transition_type":None,
        "best_path_code":None,"best_path_score":None,"alt_path_code":None,"alt_path_score":None,"path_score_gap":None,
        "queue_priority_score":None,"queue_priority_band":None,
        "ticket_ready":False,"warnings":[],"notes":[],"metadata":{},
    }

    # ── 1. Candidate scan ────────────────────────────────────────────────────
    cfg = DeepITMEntryFilterConfig(max_entry_debit_width_ratio=0.38,max_long_extrinsic_cost=10.0,
                                    min_projected_recovery_ratio=0.40,min_future_roll_score=40.0,
                                    min_open_interest=50,min_volume=5)
    candidates = []
    if getattr(context,"environment",None) in ("NEUTRAL_TIME_SPREADS",) and long_leg_quotes and short_leg_quotes:
        try:
            candidates = scan_deep_itm_calendar_candidates(context,"PUT",long_leg_quotes,
                                                            short_leg_quotes,next_generation_shorts,cfg)
        except Exception as e:
            result["warnings"].append(f"Scanner error for {symbol}: {e}")

    if candidates:
        c = candidates[0]
        cdict={"campaign_family":c.campaign_family,"entry_family":c.entry_family,"structure":c.structure,
               "entry_net_debit":c.entry_net_debit,"entry_cheapness_score":c.entry_cheapness_score,
               "future_roll_score":c.future_roll_score,"candidate_score":c.candidate_score,
               "expected_move_clearance":c.expected_move_clearance,"liquidity_score":c.liquidity_score}
        result.update({"candidate_found":True,"campaign_family":c.campaign_family,
                       "entry_family":c.entry_family,"current_structure":c.structure,
                       "current_side":c.option_type,"candidate_score":c.candidate_score,
                       "entry_cheapness_score":c.entry_cheapness_score,
                       "projected_recovery_ratio":c.projected_recovery_ratio,
                       "future_roll_score":c.future_roll_score})
        ok,errors = validate_campaign_pipeline_stage("scanner_candidate",cdict)
        if not ok: result["warnings"].append(f"Scanner candidate schema issue"); result["metadata"]["scanner_errors"]=errors

    # ── 2. Tracked campaign path ─────────────────────────────────────────────
    row = tracked_campaign_row
    if row and row.get("campaign_family") == "DEEP_ITM_CAMPAIGN":
        result.update({"campaign_id":row.get("campaign_id"),"campaign_family":row.get("campaign_family"),
                       "entry_family":row.get("entry_family"),"current_structure":row.get("current_structure"),
                       "current_side":row.get("current_side"),"net_campaign_basis":row.get("net_campaign_basis"),
                       "campaign_recovered_pct":row.get("campaign_recovered_pct"),
                       "campaign_cycle_count":row.get("campaign_cycle_count")})
        ok,errors = validate_campaign_pipeline_stage("enriched_row",row)
        if not ok: result["warnings"].append("Enriched row validation failed"); result["metadata"]["enriched_row_errors"]=errors

        snap = CampaignLedgerSnapshot(
            campaign_id=row["campaign_id"],campaign_family=row["campaign_family"],entry_family=row["entry_family"],
            opening_debit=row.get("opening_debit",0.0),opening_credit=row.get("opening_credit",0.0),
            realized_credit_collected=row.get("realized_credit_collected",0.0),
            realized_close_cost=row.get("realized_close_cost",0.0),repair_debit_paid=row.get("repair_debit_paid",0.0),
            net_campaign_basis=row.get("net_campaign_basis",0.0),campaign_recovered_pct=row.get("campaign_recovered_pct",0.0),
            campaign_cycle_count=row.get("campaign_cycle_count",0),campaign_realized_pnl=row.get("campaign_realized_pnl",0.0),
            current_structure=row.get("current_structure"),current_side=row.get("current_side"))
        ok,errors = validate_campaign_pipeline_stage("ledger_snapshot",snap)
        if not ok: result["warnings"].append("Ledger snapshot validation failed"); result["metadata"]["ledger_errors"]=errors

        # ── 3. Roll evaluation ───────────────────────────────────────────────
        rolls = evaluate_same_side_rolls(
            row["symbol"],row["current_side"],row["short_strike"],row["short_expiry"],
            row.get("current_short_close_cost",0.0),row["current_profit_percent"],
            row["campaign_recovered_pct"],row.get("proposed_same_side_shorts",[]),
            row.get("next_generation_shorts",[]),row.get("expected_move_clearance_by_strike",{}),
            row.get("liquidity_score_by_strike",{}),RollEngineConfig(),defensive_mode=False)

        # ── 4. Lifecycle ─────────────────────────────────────────────────────
        ctx = CampaignLifecycleContext(row["symbol"],row["current_structure"],row["current_side"],
            row["short_dte"],row["long_dte"],row["distance_to_strike"],row["expected_move"],
            row["current_profit_percent"],row.get("execution_surface_score",50.0),
            row.get("timing_score",50.0),row.get("regime_alignment_score",50.0),
            row.get("campaign_complexity_score",50.0))
        ld = build_campaign_lifecycle_decision(row["campaign_id"],row["campaign_family"],
            row["entry_family"],ctx,snap,same_side_rolls=rolls)
        result.update({"campaign_state":ld.campaign_state,"campaign_action":ld.campaign_action,
                       "selected_transition_type":ld.selected_transition_type})
        ok,errors = validate_campaign_pipeline_stage("lifecycle_decision",ld)
        if not ok: result["warnings"].append("Lifecycle validation failed"); result["metadata"]["lifecycle_errors"]=errors

        # ── 5. Ranking ───────────────────────────────────────────────────────
        tc = CampaignTransitionContext(row["symbol"],row["campaign_id"],row["campaign_family"],
            row["entry_family"],row["current_structure"],row["current_side"],
            row["net_campaign_basis"],row["campaign_recovered_pct"],row["campaign_cycle_count"],
            row["current_profit_percent"],(ld.roll_output or {}).get("future_roll_score",0.0),
            row.get("campaign_complexity_score",50.0),row.get("execution_surface_score",50.0),
            row.get("timing_score",50.0),row.get("regime_alignment_score",50.0),
            ld.campaign_state,ld.campaign_action,ld.campaign_urgency,ld.campaign_reason)
        transitions = build_transition_candidates(tc,same_side_rolls=rolls)
        prc = PathRankingContext(row["symbol"],"BASIS_RECOVERY",row["campaign_recovered_pct"],
            row["net_campaign_basis"],row.get("execution_surface_score",50.0),
            row.get("timing_score",50.0),row.get("regime_alignment_score",50.0),
            row.get("campaign_complexity_score",50.0),row["current_profit_percent"],
            row.get("risk_envelope"),row.get("maturity_level"))
        ranked = rank_campaign_paths(transitions,prc)
        if ranked:
            result.update({"best_path_code":ranked[0].path_code,"best_path_score":ranked[0].path_total_score})
            if len(ranked)>1:
                result.update({"alt_path_code":ranked[1].path_code,"alt_path_score":ranked[1].path_total_score,
                               "path_score_gap":round(ranked[0].path_total_score-ranked[1].path_total_score,6)})
            ok,errors = validate_campaign_pipeline_stage("ranked_path",ranked[0])
            if not ok: result["warnings"].append("Ranked path validation failed"); result["metadata"]["ranked_path_errors"]=errors

        # ── 6. Queue row ─────────────────────────────────────────────────────
        qctx = CampaignQueueContext(environment,row["symbol"],row.get("position_id"),
            row["campaign_id"],row["campaign_family"],row["entry_family"],
            row["current_structure"],row["current_side"],row.get("short_strike"),row.get("long_strike"),
            row.get("short_expiry"),row.get("long_expiry"),row.get("short_dte"),row.get("long_dte"),
            row.get("current_profit_percent"),row.get("distance_to_strike"),row.get("expected_move"),
            row.get("execution_surface_score"),row.get("timing_score"),row.get("regime_alignment_score"),
            row.get("campaign_complexity_score"),row.get("deployment_label"),row.get("risk_envelope"),row.get("maturity_level"))
        qrow = build_transition_queue_row(qctx,snap,ld,ranked)
        result.update({"queue_priority_score":qrow.queue_priority_score,"queue_priority_band":qrow.queue_priority_band})
        ok,errors = validate_campaign_pipeline_stage("queue_row",qrow)
        if not ok: result["warnings"].append("Queue row validation failed"); result["metadata"]["queue_row_errors"]=errors

        # ── 7. Workspace + ticket ────────────────────────────────────────────
        wi = CampaignWorkspaceInput(environment,row["symbol"],row.get("position_id"),
            row["campaign_id"],row["campaign_family"],row["entry_family"],
            row["current_structure"],row["current_side"],row.get("short_strike"),row.get("long_strike"),
            row.get("short_expiry"),row.get("long_expiry"),row.get("short_dte"),row.get("long_dte"),
            row.get("current_profit_percent"),row.get("execution_surface_score"),row.get("timing_score"),
            row.get("regime_alignment_score"),row.get("linked_review_ids",[]),
            row.get("knowledge_context_summaries",[]),row.get("campaign_reason",""))
        ws = build_campaign_path_execution_workspace(wi,snap,ld,ranked)
        ok,errors = validate_campaign_pipeline_stage("workspace",ws)
        if not ok: result["warnings"].append("Workspace validation failed"); result["metadata"]["workspace_errors"]=errors

        ti = CampaignTransitionTicketInput(environment=ws.environment,symbol=ws.symbol,
            position_id=ws.position_id,campaign_id=ws.campaign_id,campaign_family=ws.campaign_family,
            entry_family=ws.entry_family,current_structure=ws.current_structure,current_side=ws.current_side,
            campaign_state=ws.campaign_state["campaign_state"],campaign_action=ws.campaign_state["campaign_action"],
            campaign_urgency=ws.campaign_state["campaign_urgency"],campaign_reason=ws.campaign_state["campaign_reason"],
            opening_debit=ws.campaign_ledger["opening_debit"],opening_credit=ws.campaign_ledger["opening_credit"],
            realized_credit_collected=ws.campaign_ledger["realized_credit_collected"],
            realized_close_cost=ws.campaign_ledger["realized_close_cost"],
            repair_debit_paid=ws.campaign_ledger["repair_debit_paid"],
            net_campaign_basis=ws.campaign_ledger["net_campaign_basis"],
            campaign_recovered_pct=ws.campaign_ledger["campaign_recovered_pct"],
            campaign_cycle_count=ws.campaign_ledger["campaign_cycle_count"],
            campaign_realized_pnl=ws.campaign_ledger["campaign_realized_pnl"],
            selected_path=ws.selected_path,alternative_path=ws.alternative_path,
            deployment_label=row.get("deployment_label"),risk_envelope=row.get("risk_envelope"),
            maturity_level=row.get("maturity_level"),linked_review_ids=ws.linked_review_ids,
            knowledge_context_summaries=ws.knowledge_context_summaries,primary_rationale=ws.primary_rationale)
        ticket = build_campaign_transition_ticket(ti)
        result["ticket_ready"] = bool(ticket.selected_path)
        ok,errors = validate_campaign_pipeline_stage("ticket",ticket)
        if not ok: result["warnings"].append("Ticket validation failed"); result["metadata"]["ticket_errors"]=errors
        result["notes"].append(f"{symbol}: state={result['campaign_state']}, best_path={result['best_path_code']}, queue={result['queue_priority_band']}")

    return result

def run_live_validation_batch(environment: str, context_by_symbol: dict[str,Any],
                               long_leg_quotes_by_symbol: dict[str,list[Any]],
                               short_leg_quotes_by_symbol: dict[str,list[Any]],
                               next_generation_shorts_by_symbol: dict[str,list[Any]],
                               tracked_campaign_rows_by_symbol: dict[str,dict[str,Any]]|None=None) -> list[dict[str,Any]]:
    tracked = tracked_campaign_rows_by_symbol or {}
    out = []
    for sym in SYMBOLS:
        ctx = context_by_symbol.get(sym)
        if ctx is None:
            out.append({"symbol":sym,"timestamp_utc":_utcnow(),"environment":environment,
                        "candidate_found":False,"ticket_ready":False,
                        "warnings":[f"No market context supplied for {sym}."],"notes":[],"metadata":{}})
            continue
        out.append(validate_symbol_live(sym,environment,ctx,
            long_leg_quotes_by_symbol.get(sym,[]),short_leg_quotes_by_symbol.get(sym,[]),
            next_generation_shorts_by_symbol.get(sym,[]),tracked.get(sym)))
    return out
