"""validation/live_validation_reporter.py — Summarize + render validation results."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

@dataclass(slots=True)
class LiveValidationSummary:
    total_symbols: int; candidate_found_count: int; ticket_ready_count: int; warning_count: int
    roll_ready_count: int; defensive_count: int; bank_reduce_count: int
    best_path_roll_count: int; best_path_flip_count: int; best_path_collapse_count: int
    act_now_count: int; decide_now_count: int; watch_closely_count: int; improve_later_count: int

def _count(results: list[dict], fn) -> int:
    return sum(1 for r in results if fn(r))

def summarize_live_validation_results(results: list[dict[str,Any]]) -> LiveValidationSummary:
    return LiveValidationSummary(
        total_symbols=len(results),
        candidate_found_count=_count(results,lambda r:bool(r.get("candidate_found"))),
        ticket_ready_count=_count(results,lambda r:bool(r.get("ticket_ready"))),
        warning_count=sum(len(r.get("warnings",[])) for r in results),
        roll_ready_count=_count(results,lambda r:r.get("campaign_state")=="ROLL_READY"),
        defensive_count=_count(results,lambda r:r.get("campaign_state")=="DEFENSIVE_ROLL"),
        bank_reduce_count=_count(results,lambda r:r.get("campaign_state")=="BANK_REDUCE"),
        best_path_roll_count=_count(results,lambda r:r.get("best_path_code")=="ROLL_SAME_SIDE"),
        best_path_flip_count=_count(results,lambda r:r.get("best_path_code")=="FLIP_SELECTIVELY"),
        best_path_collapse_count=_count(results,lambda r:r.get("best_path_code")=="COLLAPSE_TO_SPREAD"),
        act_now_count=_count(results,lambda r:r.get("queue_priority_band")=="ACT_NOW"),
        decide_now_count=_count(results,lambda r:r.get("queue_priority_band")=="DECIDE_NOW"),
        watch_closely_count=_count(results,lambda r:r.get("queue_priority_band")=="WATCH_CLOSELY"),
        improve_later_count=_count(results,lambda r:r.get("queue_priority_band")=="IMPROVE_LATER"))

def live_validation_summary_to_dict(s: LiveValidationSummary) -> dict[str,Any]:
    return {"total_symbols":s.total_symbols,"candidate_found_count":s.candidate_found_count,
            "ticket_ready_count":s.ticket_ready_count,"warning_count":s.warning_count,
            "roll_ready_count":s.roll_ready_count,"defensive_count":s.defensive_count,
            "bank_reduce_count":s.bank_reduce_count,"best_path_roll_count":s.best_path_roll_count,
            "best_path_flip_count":s.best_path_flip_count,"best_path_collapse_count":s.best_path_collapse_count,
            "act_now_count":s.act_now_count,"decide_now_count":s.decide_now_count,
            "watch_closely_count":s.watch_closely_count,"improve_later_count":s.improve_later_count}

def build_symbol_report_row(result: dict[str,Any]) -> dict[str,Any]:
    return {"symbol":result.get("symbol"),"regime_environment":result.get("regime_environment"),
            "candidate_found":result.get("candidate_found"),"campaign_family":result.get("campaign_family"),
            "entry_family":result.get("entry_family"),"campaign_state":result.get("campaign_state"),
            "campaign_action":result.get("campaign_action"),"best_path_code":result.get("best_path_code"),
            "best_path_score":result.get("best_path_score"),"queue_priority_band":result.get("queue_priority_band"),
            "queue_priority_score":result.get("queue_priority_score"),"ticket_ready":result.get("ticket_ready"),
            "warning_count":len(result.get("warnings",[])),"warnings":result.get("warnings",[]),
            "notes":result.get("notes",[])}

def build_live_validation_report(results: list[dict[str,Any]]) -> dict[str,Any]:
    return {"summary":live_validation_summary_to_dict(summarize_live_validation_results(results)),
            "rows":[build_symbol_report_row(r) for r in results]}

def render_live_validation_report_text(results: list[dict[str,Any]]) -> str:
    report=build_live_validation_report(results); s=report["summary"]; rows=report["rows"]
    lines=["LIVE VALIDATION SUMMARY",
           f"symbols={s['total_symbols']} | candidates={s['candidate_found_count']} | tickets={s['ticket_ready_count']} | warnings={s['warning_count']}",
           f"states: roll_ready={s['roll_ready_count']} | defensive={s['defensive_count']} | bank_reduce={s['bank_reduce_count']}",
           f"best_paths: roll={s['best_path_roll_count']} | flip={s['best_path_flip_count']} | collapse={s['best_path_collapse_count']}",
           f"queue_bands: act_now={s['act_now_count']} | decide_now={s['decide_now_count']} | watch_closely={s['watch_closely_count']} | improve_later={s['improve_later_count']}",""]
    for row in rows:
        lines.append(f"{row['symbol']}: regime={row['regime_environment']} | candidate={row['candidate_found']} | "
                     f"state={row['campaign_state']} | path={row['best_path_code']} | "
                     f"queue={row['queue_priority_band']} | ticket={row['ticket_ready']} | warnings={row['warning_count']}")
        for w in row["warnings"]: lines.append(f"  WARNING: {w}")
        for n in row["notes"]: lines.append(f"  NOTE: {n}")
    return "\n".join(lines)
