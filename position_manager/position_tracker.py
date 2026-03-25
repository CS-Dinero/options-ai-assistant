"""
position_manager/position_tracker.py
Tracks open positions and surfaces roll/convert/exit signals.

PRIMARY SOURCE:  logs/trade_log.csv (rows where date_close is blank)
FALLBACK/OVERRIDE: data/positions/open_positions.csv (manual CSV)

Priority rule:
  1. Trade log is the default truth.
  2. Manual CSV rows supplement the trade log if they contain a trade_id
     not already in the log, OR override a log row if the CSV row has
     a matching trade_id with more recent data.
  3. If a manual CSV row has no trade_id, it is treated as supplemental.

Why this design:
  - Zero friction for existing workflow (trade log already exists)
  - Manual override available for broker-sourced position data
  - No data entry required unless you want to supplement
"""

from __future__ import annotations

import csv
import os
from datetime import date, datetime
from pathlib import Path
from typing import Any

from position_manager.calendar_diagonal_engine import (
    CalDiagConfig, OpenCalDiagPosition, evaluate_position,
    decision_to_dict,
)


# ─────────────────────────────────────────────
# DEFAULTS
# ─────────────────────────────────────────────

DEFAULT_TRADE_LOG  = Path("logs/trade_log.csv")
DEFAULT_MANUAL_CSV = Path("data/positions/open_positions.csv")

_CALENDAR_DIAGONAL_TYPES = {"calendar", "diagonal"}
_CREDIT_TYPES            = {"bull_put", "bear_call"}
_DEBIT_TYPES             = {"bull_call_debit", "bear_put_debit"}


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _sf(v: Any, default: float | None = None) -> float | None:
    try:
        return float(v) if v not in (None, "", "null", "—") else default
    except (TypeError, ValueError):
        return default


def _si(v: Any, default: int = 0) -> int:
    try:
        return int(float(v)) if v not in (None, "", "null") else default
    except (TypeError, ValueError):
        return default


def _is_open(row: dict) -> bool:
    """A trade is open if date_close is blank, null, or missing."""
    dc = row.get("date_close", "")
    return not dc or str(dc).strip() in ("", "null", "None")


def _compute_dte(expiration: str) -> int:
    try:
        exp = datetime.strptime(expiration.strip(), "%Y-%m-%d").date()
        return max(0, (exp - date.today()).days)
    except (ValueError, AttributeError):
        return 0


def _credit_management_status(row: dict, spot: float | None) -> str:
    """
    Quick credit spread management signal without full scoring.
    Returns: HOLD / REVIEW_OR_ROLL / CLOSE_STOP / CLOSE_TIME
    """
    entry   = abs(_sf(row.get("entry_price", row.get("entry_debit_credit", 0))) or 0)
    target  = _sf(row.get("target_price",   row.get("target_exit_value")))
    stop    = _sf(row.get("stop_price",     row.get("stop_value")))
    short_dte = _si(row.get("short_dte"), _compute_dte(row.get("short_expiration", "")))

    from config.settings import TIME_EXIT_DTE
    if short_dte <= TIME_EXIT_DTE:
        return "CLOSE_TIME"
    if target is not None and entry <= target:
        return "CLOSE_TP"
    if stop is not None and entry >= stop:
        return "CLOSE_STOP"

    if spot and row.get("short_strike"):
        short_k = _sf(row["short_strike"])
        st_type = row.get("strategy_type", "")
        if st_type == "bull_put" and spot <= (short_k or 999):
            return "REVIEW_OR_ROLL"
        if st_type == "bear_call" and spot >= (short_k or 0):
            return "REVIEW_OR_ROLL"

    return "HOLD"


# ─────────────────────────────────────────────
# LOADERS
# ─────────────────────────────────────────────

def load_open_from_trade_log(path: Path | str | None = None) -> list[dict]:
    """
    Load all open trades from trade_log.csv.
    Returns list of row dicts where date_close is blank.
    """
    filepath = Path(path) if path else DEFAULT_TRADE_LOG
    if not filepath.exists():
        return []
    rows = []
    try:
        with open(filepath, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if _is_open(row):
                    rows.append(dict(row))
    except Exception:
        pass
    return rows


def load_manual_positions(path: Path | str | None = None) -> list[dict]:
    """
    Load manual override / supplement positions from CSV.
    Expected columns mirror trade_log.csv schema but only a subset is required.
    """
    filepath = Path(path) if path else DEFAULT_MANUAL_CSV
    if not filepath.exists():
        return []
    rows = []
    try:
        with open(filepath, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                rows.append(dict(row))
    except Exception:
        pass
    return rows


def merge_positions(
    log_rows:    list[dict],
    manual_rows: list[dict],
) -> list[dict]:
    """
    Merge trade-log positions with manual CSV positions.

    Priority rules:
      - Manual row with matching trade_id OVERRIDES the log row.
      - Manual row with NO trade_id (or unknown id) is APPENDED as supplemental.
      - Trade log rows with no manual counterpart are kept as-is.
    """
    # Index log rows by trade_id
    merged: dict[str, dict] = {}
    supplemental: list[dict] = []

    for row in log_rows:
        tid = row.get("trade_id", "")
        if tid:
            merged[tid] = row

    for row in manual_rows:
        tid = row.get("trade_id", "")
        if tid and tid in merged:
            # Manual data overrides matching log row
            merged[tid] = {**merged[tid], **{k: v for k, v in row.items() if v not in ("", None)}}
        elif tid:
            merged[tid] = row
        else:
            supplemental.append(row)

    return list(merged.values()) + supplemental


# ─────────────────────────────────────────────
# POSITION TRACKER
# ─────────────────────────────────────────────

class PositionTracker:
    """
    Tracks open positions and surfaces actionable signals.

    Usage:
        tracker = PositionTracker()
        snapshot = tracker.snapshot(derived=derived_context, spot=669.03)
        for pos in snapshot["calendar_diagonal"]:
            print(pos["decision"]["action"])
        for pos in snapshot["credit_spreads"]:
            print(pos["management_status"])
    """

    def __init__(
        self,
        trade_log_path:  Path | str | None = None,
        manual_csv_path: Path | str | None = None,
        cfg:             CalDiagConfig     | None = None,
    ):
        self.trade_log_path  = Path(trade_log_path)  if trade_log_path  else DEFAULT_TRADE_LOG
        self.manual_csv_path = Path(manual_csv_path) if manual_csv_path else DEFAULT_MANUAL_CSV
        self.cfg             = cfg or CalDiagConfig()

    def load_all_open(self) -> list[dict]:
        """Load and merge all open positions from both sources."""
        log_rows    = load_open_from_trade_log(self.trade_log_path)
        manual_rows = load_manual_positions(self.manual_csv_path)
        return merge_positions(log_rows, manual_rows)

    def snapshot(
        self,
        derived: dict | None = None,
        spot:    float | None = None,
    ) -> dict[str, Any]:
        """
        Build a full position snapshot with management signals.

        Returns:
            {
                "total_open":        int,
                "calendar_diagonal": list[dict],   # with lifecycle decision
                "credit_spreads":    list[dict],   # with EGPE management status
                "debit_spreads":     list[dict],   # with simple hold/exit signal
                "other":             list[dict],   # unclassified
                "summary":           dict,         # counts + urgency rollup
            }
        """
        all_open = self.load_all_open()

        derived = derived or {}
        live_spot = spot or derived.get("spot_price") or 0.0
        vga       = derived.get("vga_environment", "mixed")
        gamma_r   = derived.get("gamma_regime", "unknown")
        iv_r      = derived.get("iv_regime", "unknown")
        em        = derived.get("expected_move", 0.0)

        cal_diag     : list[dict] = []
        credit_sp    : list[dict] = []
        debit_sp     : list[dict] = []
        other        : list[dict] = []

        for row in all_open:
            st = row.get("strategy_type", "").lower()

            if st in _CALENDAR_DIAGONAL_TYPES:
                enriched = self._eval_cal_diag(row, live_spot, vga, gamma_r, iv_r, em)
                cal_diag.append(enriched)

            elif st in _CREDIT_TYPES:
                row["management_status"] = _credit_management_status(row, live_spot)
                row["live_spot"]         = live_spot
                # Attach VH harvest fields to credit spreads too
                try:
                    from position_manager.harvest_engine import build_harvest_summary
                    from position_manager.vh_triggers import evaluate_vh_triggers
                    from engines.sentiment_pivot_engine import recommend_sentiment_pivot
                    mctx = {"spot_price": live_spot, "gamma_regime": gamma_r,
                            "iv_regime": iv_r, "vga_environment": vga,
                            "gamma_trap": None}
                    flip_dict = recommend_sentiment_pivot(row, mctx, sentiment_score=0.0)
                    flip_rec  = flip_dict.get("pivot_recommendation", "HOLD_STRUCTURE")
                    triggers  = evaluate_vh_triggers(row, mctx)
                    row["vh_triggers"] = triggers
                    harvest = build_harvest_summary(row, mctx, flip_rec)
                    try:
                        from engines.scaling_harvest_bot import build_bot_summary
                        bot = build_bot_summary(row, mctx)
                    except Exception:
                        bot = {"bot_action":"HOLD","bot_priority":6,"urgency":"LOW",
                               "rationale":"","recommended_contract_add":0}
                    row.update({
                        "net_liq":                  harvest["net_liq"],
                        "harvestable_equity":       harvest["harvestable_equity"],
                        "proposed_roll_credit":     harvest["proposed_roll_credit"],
                        "harvest_badge":            harvest["harvest_badge"],
                        "gamma_trap_distance":      harvest["gamma_trap_distance"],
                        "flip_recommendation":      flip_rec,
                        "sentiment_score":          0.0,
                        "bot_action":               bot["bot_action"],
                        "bot_priority":             bot["bot_priority"],
                        "urgency":                  bot["urgency"],
                        "bot_rationale":            bot["rationale"],
                        "recommended_contract_add": bot["recommended_contract_add"],
                    })
                except Exception:
                    pass
                credit_sp.append(row)

            elif st in _DEBIT_TYPES:
                # Simple time-based signal for debit spreads
                short_dte = _si(row.get("short_dte"), _compute_dte(row.get("short_expiration", "")))
                from config.settings import TIME_EXIT_DTE
                row["management_status"] = "CLOSE_TIME" if short_dte <= TIME_EXIT_DTE else "HOLD"
                row["live_spot"]         = live_spot
                debit_sp.append(row)

            else:
                other.append(row)

        # Urgency rollup
        high   = sum(1 for p in cal_diag if p.get("decision", {}).get("urgency") == "HIGH")
        medium = sum(1 for p in cal_diag if p.get("decision", {}).get("urgency") == "MEDIUM")
        close_signals = sum(1 for p in credit_sp + debit_sp
                            if "CLOSE" in p.get("management_status", ""))

        return {
            "total_open":        len(all_open),
            "calendar_diagonal": cal_diag,
            "credit_spreads":    credit_sp,
            "debit_spreads":     debit_sp,
            "other":             other,
            "summary": {
                "high_urgency":    high,
                "medium_urgency":  medium,
                "close_signals":   close_signals,
                "total_positions": len(all_open),
                "vga_environment": vga,
            },
        }

    def _eval_cal_diag(
        self,
        row:     dict,
        spot:    float,
        vga:     str,
        gamma_r: str,
        iv_r:    str,
        em:      float,
    ) -> dict:
        """Build an OpenCalDiagPosition from a trade row and evaluate it."""
        entry   = abs(_sf(row.get("entry_debit_credit", row.get("entry_price", 0))) or 0)
        current = abs(_sf(row.get("current_value",      row.get("exit_price",  entry))) or entry)
        long_k  = _sf(row.get("long_strike")) or spot
        short_k = _sf(row.get("short_strike")) or spot
        l_dte   = _si(row.get("long_dte"),  _compute_dte(row.get("long_expiration",  "")))
        s_dte   = _si(row.get("short_dte"), _compute_dte(row.get("short_expiration", "")))

        # Infer option side from direction or strategy_type
        direction = str(row.get("direction", row.get("strategy_type", ""))).lower()
        option_side = "put" if "put" in direction or "bear" in direction else "call"

        pos = OpenCalDiagPosition(
            symbol=row.get("symbol", ""),
            structure_type=row.get("strategy_type", "calendar"),
            option_side=option_side,
            long_strike=long_k,
            short_strike=short_k,
            long_dte=l_dte,
            short_dte=s_dte,
            entry_debit=entry,
            current_value=current,
            spot=spot if spot else _sf(row.get("spot_open")) or 0.0,
            expected_move=em if em else _sf(row.get("expected_move")) or 0.0,
            vga_environment=vga,
            gamma_regime=gamma_r,
            iv_regime=iv_r,
        )

        decision = evaluate_position(pos, self.cfg)
        enriched = dict(row)
        enriched["decision"]    = decision_to_dict(decision)
        enriched["live_spot"]   = spot
        enriched["live_vga"]    = vga

        # ── VH harvest layer (additive) ───────────────────────────────────────
        try:
            from position_manager.vh_triggers import evaluate_vh_triggers
            from position_manager.harvest_engine import build_harvest_summary
            from engines.sentiment_pivot_engine import recommend_sentiment_pivot

            mctx = {
                "spot_price":      spot or 0.0,
                "gamma_regime":    gamma_r,
                "iv_regime":       iv_r,
                "vga_environment": vga,
                "gamma_trap":      row.get("gamma_trap_strike"),
                "put_25d_iv":      row.get("put_25d_iv"),
                "call_25d_iv":     row.get("call_25d_iv"),
                "expected_move":   em,
            }
            sentiment = float(row.get("sentiment_score", 0.0))
            flip_dict = recommend_sentiment_pivot(enriched, mctx, sentiment_score=sentiment)
            flip_rec  = flip_dict.get("pivot_recommendation", "HOLD_STRUCTURE")

            triggers  = evaluate_vh_triggers(enriched, mctx)
            enriched["vh_triggers"] = triggers

            harvest = build_harvest_summary(enriched, mctx, flip_rec)

            # v26.1: scored flip optimizer
            try:
                from engines.flip_optimizer import choose_best_flip
                flip_opt = choose_best_flip(enriched, mctx)
                if flip_opt.get("flip_candidate"):
                    flip_rec = flip_opt["recommendation"]
            except Exception:
                flip_opt = {"flip_candidate": False, "recommendation": flip_rec,
                            "flip_quality_score": 0.0}

            # Scaling bot — runs after harvest + flip are computed
            try:
                from engines.scaling_harvest_bot import build_bot_summary
                bot = build_bot_summary(enriched, mctx)
            except Exception:
                bot = {"bot_action":"HOLD","bot_priority":6,"urgency":"LOW",
                       "rationale":"Bot unavailable.","recommended_contract_add":0}

            # Live strike selector — propose replacement structures if chain available
            roll_candidate_inputs = []
            roll_preview = None
            try:
                live_chain = enriched.get("_live_chain", [])
                if live_chain:
                    from engines.live_strike_selector import build_live_roll_candidates
                    from position_manager.roll_credit_calculator import calculate_best_roll
                    roll_candidate_inputs = build_live_roll_candidates(
                        enriched, mctx, live_chain)[:5]
                    if roll_candidate_inputs:
                        roll_preview = calculate_best_roll(
                            enriched, mctx, roll_candidate_inputs)
            except Exception:
                pass

            # Skew-flip transition engine — runs on calendars and diagonals
            transition_result = {}
            try:
                structure_t = str(enriched.get("strategy_type","")).lower()
                long_leg_d  = enriched.get("long_leg") or {}
                short_leg_d = enriched.get("short_leg") or {}
                # Need at minimum a short_leg dict to run transition engine
                if not short_leg_d and enriched.get("short_strike"):
                    short_leg_d = {
                        "option_type": enriched.get("option_side","call"),
                        "strike":      float(enriched.get("short_strike",0)),
                        "expiry":      enriched.get("short_expiration",""),
                        "expiration":  enriched.get("short_expiration",""),
                        "dte":         int(float(enriched.get("short_dte",7))),
                        "bid":  float(enriched.get("current_short_mid",0) or 0),
                        "ask":  float(enriched.get("current_short_mid",0) or 0)*1.05,
                        "mid":  float(enriched.get("current_short_mid",0) or 0),
                        "delta":float(enriched.get("short_delta",0) or 0),
                    }
                if not long_leg_d and enriched.get("long_strike"):
                    long_leg_d = {
                        "option_type": enriched.get("option_side","call"),
                        "strike":      float(enriched.get("long_strike",0)),
                        "expiry":      enriched.get("long_expiration",""),
                        "expiration":  enriched.get("long_expiration",""),
                        "dte":         int(float(enriched.get("long_dte",30))),
                        "bid":  float(enriched.get("current_long_mid",0) or 0)*0.95,
                        "ask":  float(enriched.get("current_long_mid",0) or 0)*1.05,
                        "mid":  float(enriched.get("current_long_mid",0) or 0),
                        "delta":0.90,
                    }

                live_chain = enriched.get("_live_chain", [])
                if live_chain and short_leg_d and long_leg_d and                         "calendar" in structure_t or "diagonal" in structure_t:
                    from engines.skew_flip_harvest_engine import evaluate_skew_flip_transition
                    chain_bundle = {
                        "calls": [r for r in live_chain if str(r.get("option_type","")).lower()=="call"],
                        "puts":  [r for r in live_chain if str(r.get("option_type","")).lower()=="put"],
                        "put_side_richness":  float(mctx.get("put_25d_iv",0) or 0),
                        "call_side_richness": float(mctx.get("call_25d_iv",0) or 0),
                    }
                    pos_for_transition = {
                        **enriched,
                        "long_leg":  long_leg_d,
                        "short_leg": short_leg_d,
                        "current_risk_basis": abs(_sf(enriched.get("entry_debit_credit")
                                                    or enriched.get("entry_price",0.85))),
                    }
                    transition_result = evaluate_skew_flip_transition(
                        current_position=pos_for_transition,
                        chain_bundle=chain_bundle,
                        spot=float(mctx.get("spot_price",0)),
                        market_context=mctx,
                    )
            except Exception:
                transition_result = {}

            # Attach transition fields
            # Initialize campaign memory for this position
            if not enriched.get("campaign_memory"):
                try:
                    from position_manager.campaign_memory import (
                        initialize_campaign_memory, compute_campaign_net_basis, compute_recovered_pct)
                    cm = initialize_campaign_memory(enriched)
                    enriched["campaign_memory"]          = cm
                    enriched["campaign_net_basis"]       = compute_campaign_net_basis(cm)
                    enriched["campaign_recovered_pct"]   = compute_recovered_pct(cm)
                    enriched["campaign_harvest_cycles"]  = 0
                    enriched["campaign_flip_count"]      = 0
                    enriched["campaign_rebuild_count"]   = 0
                except Exception:
                    pass

            enriched["transition_action"]           = transition_result.get("recommended_action","HOLD_CURRENT_HARVEST")
            enriched["transition_net_credit"]       = transition_result.get("transition_net_credit",0.0)
            enriched["transition_future_roll_score"]= transition_result.get("future_roll_score",0.0)
            enriched["transition_structure_score"]  = transition_result.get("composite_score",0.0)
            enriched["transition_side_edge"]        = transition_result.get("side_edge")
            enriched["transition_is_credit_approved"]= transition_result.get("approved",False)
            enriched["transition_summary"]          = transition_result.get("transition_summary","")
            enriched["transition_why"]              = transition_result.get("why",[])
            enriched["transition_new_structure_type"]= (transition_result.get("new_structure") or {}).get("type","")
            enriched["transition_new_long_leg"]     = (transition_result.get("new_structure") or {}).get("long_leg")
            enriched["transition_new_short_leg"]    = (transition_result.get("new_structure") or {}).get("short_leg")
            enriched["transition_rejected_candidates"]= transition_result.get("rejected_candidates",[])
            # Analyst narrative
            try:
                from analyst.narrative_engine import build_transition_narrative
                from analyst.desk_summary_engine import build_queue_one_liner, build_blocked_one_liner, build_campaign_one_liner
                from dashboard.ui_state_helpers import build_operational_tags
                narrative = build_transition_narrative(enriched)
                enriched["transition_winner_reasons"]    = narrative.get("winner_reasons",[])
                enriched["transition_winner_summary"]    = narrative.get("winner_summary","")
                enriched["transition_rejection_summary"] = narrative.get("rejection_summary","")
                enriched["transition_invalidation_notes"]= narrative.get("invalidation_notes",[])
                enriched["transition_invalidation_summary"]=narrative.get("invalidation_summary","")
                enriched["transition_next_roll_notes"]   = narrative.get("next_roll_notes",[])
                enriched["transition_next_roll_summary"] = narrative.get("next_roll_summary","")
                enriched["transition_desk_note"]         = narrative.get("desk_note","")
                enriched["queue_one_liner"]   = build_queue_one_liner(enriched)
                enriched["blocked_one_liner"] = build_blocked_one_liner(enriched)
                enriched["campaign_one_liner"]= build_campaign_one_liner(enriched)
                enriched["operational_tags"]  = build_operational_tags(enriched)
            except Exception:
                pass

            # Playbook matching + SOP + audit tags
            try:
                from playbooks.playbook_matcher import build_playbook_match
                from playbooks.sop_renderer import render_playbook_sop
                from playbooks.playbook_audit_tags import build_playbook_audit_tags
                pb = build_playbook_match(enriched)
                enriched.update(pb)
                sop = render_playbook_sop(enriched)
                enriched["sop_setup"]        = sop.get("sop_setup",[])
                enriched["sop_execution"]    = sop.get("sop_execution",[])
                enriched["sop_invalidation"] = sop.get("sop_invalidation",[])
                enriched["sop_next_step"]    = sop.get("sop_next_step",[])
                enriched["playbook_audit_tags"] = build_playbook_audit_tags(enriched)
            except Exception: pass

            # Capital rotation (requires playbook_code to exist first)
            try:
                from portfolio.capital_rotation_engine import evaluate_capital_rotation
                rot = evaluate_capital_rotation(enriched_rows_so_far, enriched)
                enriched["playbook_status"]              = rot.get("effective_status","WATCHLIST")
                enriched["playbook_size_multiplier"]     = rot.get("size_multiplier",1.0)
                enriched["playbook_quality_multiplier"]  = rot.get("quality_multiplier",1.0)
                enriched["transition_final_contract_add"]= rot.get("final_contract_add",0)
                enriched["active_symbol_count"]          = rot.get("active_symbol_count",0)
                enriched["active_playbook_count"]        = rot.get("active_playbook_count",0)
                enriched["symbol_concurrency_ok"]        = rot.get("symbol_concurrency_ok",True)
                enriched["playbook_concurrency_ok"]      = rot.get("playbook_concurrency_ok",True)
                enriched["capital_commitment_decision"]  = rot.get("capital_commitment_decision","NO_ADD")
                enriched["capital_commitment_ok"]        = rot.get("capital_commitment_ok",False)
                # Playbook queue bias (from governed registry if available)
                enriched.setdefault("playbook_queue_bias", 0.0)
            except Exception:
                enriched.setdefault("playbook_status","WATCHLIST")
                enriched.setdefault("playbook_queue_bias",0.0)
                enriched.setdefault("capital_commitment_decision","NO_ADD")
                enriched.setdefault("capital_commitment_ok",False)
                enriched.setdefault("transition_final_contract_add",0)

            # Rebuild class + campaign + path fields
            enriched["transition_rebuild_class"]       = transition_result.get("rebuild_class","KEEP_LONG")
            enriched["transition_new_long_leg"]        = (transition_result.get("new_structure") or {}).get("long_leg")
            enriched["transition_new_short_leg"]       = (transition_result.get("new_structure") or {}).get("short_leg")
            enriched["transition_target_width"]        = (transition_result.get("new_structure") or {}).get("target_width")
            enriched["transition_campaign_net_basis_before"] = transition_result.get("campaign_net_basis_before",0.0)
            enriched["transition_campaign_net_basis_after"]  = transition_result.get("campaign_net_basis_after",0.0)
            enriched["transition_basis_reduction"]     = transition_result.get("basis_reduction",0.0)
            enriched["transition_recovered_pct_before"]= transition_result.get("recovered_pct_before",0.0)
            enriched["transition_recovered_pct_after"] = transition_result.get("recovered_pct_after",0.0)
            enriched["transition_campaign_improvement_score"] = transition_result.get("campaign_improvement_score",0.0)
            enriched["transition_improves_campaign"]   = transition_result.get("transition_improves_campaign",False)
            enriched["transition_avg_path_score"]      = transition_result.get("avg_path_score",0.0)
            enriched["transition_worst_path_score"]    = transition_result.get("worst_path_score",0.0)
            enriched["transition_best_path_score"]     = transition_result.get("best_path_score",0.0)
            enriched["transition_path_robust"]         = transition_result.get("path_robust",False)
            enriched["transition_scenario_results"]    = transition_result.get("scenario_results",[])
            enriched["transition_composite_score_pre_bias"] = transition_result.get("composite_score_pre_bias",0.0)
            enriched["transition_empirical_bias_total"]= transition_result.get("empirical_bias_total",0.0)
            # Portfolio fit (requires full portfolio_state — default to OK until portfolio layer runs)
            # Timing + surface + stagger fields
            enriched["transition_timing_score"]          = transition_result.get("timing_score",0.0)
            enriched["transition_timing_ok"]             = transition_result.get("timing_ok",False)
            enriched["transition_time_window"]           = transition_result.get("time_window","OUTSIDE_RTH")
            enriched["transition_execution_surface_score"]= transition_result.get("execution_surface_score",0.0)
            enriched["transition_execution_surface_ok"]  = transition_result.get("execution_surface_ok",False)
            enriched["transition_surface_local_richness"]= transition_result.get("surface_local_richness",0.0)
            enriched["transition_surface_front_back_edge"]=transition_result.get("surface_front_back_edge",0.0)
            enriched["transition_surface_term_score"]    = transition_result.get("surface_term_score",0.0)
            enriched["transition_surface_harvest_curve_score"]=transition_result.get("surface_harvest_curve_score",0.0)
            enriched["transition_execution_policy"]      = transition_result.get("execution_policy","DELAY")
            enriched["transition_size_fraction_now"]     = transition_result.get("size_fraction_now",0.0)
            enriched["transition_size_fraction_later"]   = transition_result.get("size_fraction_later",1.0)
            enriched["transition_execution_schedule"]    = transition_result.get("execution_schedule","DEFER")
            enriched["transition_next_window"]           = transition_result.get("next_window")
            # Fill quality placeholders
            enriched.setdefault("transition_latest_fill_score",0.0)
            enriched.setdefault("transition_latest_slippage_dollars",0.0)
            enriched.setdefault("transition_latest_slippage_pct",0.0)
            enriched.setdefault("transition_portfolio_fit_ok", True)
            enriched.setdefault("transition_allocator_score", 75.0)
            enriched.setdefault("transition_recycling_score", transition_result.get("basis_reduction",0.0)*20)

            enriched_rows_so_far = []  # will be empty on first pass; populated after loop
            enriched.update({
                "net_liq":                  harvest["net_liq"],
                "harvestable_equity":       harvest["harvestable_equity"],
                "proposed_roll_credit":     harvest["proposed_roll_credit"],
                "harvest_badge":            harvest["harvest_badge"],
                "gamma_trap_distance":      harvest["gamma_trap_distance"],
                "flip_recommendation":      flip_rec,
                "flip_quality_score":       flip_opt.get("flip_quality_score", 0.0),
                "flip_candidate":           flip_opt.get("flip_candidate", False),
                "sentiment_score":          sentiment,
                "harvest_summary":          harvest,
                "flip_summary":             flip_opt,
                "bot_action":               bot["bot_action"],
                "bot_priority":             bot["bot_priority"],
                "urgency":                  bot["urgency"],
                "bot_rationale":            bot["rationale"],
                "recommended_contract_add": bot["recommended_contract_add"],
                "bot_summary":              bot,
                "roll_candidate_inputs":    roll_candidate_inputs,
                "roll_preview":             roll_preview,
            })
        except Exception:
            pass

        return enriched
