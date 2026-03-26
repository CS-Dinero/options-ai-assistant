"""reporting/daily_desk_summary.py — Today's operating picture."""
from __future__ import annotations
from typing import Any
from reporting.report_builder import build_report_envelope

def build_daily_desk_summary(environment: str, live_policy_version_id: str|None,
                              global_context: dict[str,Any], portfolio_state: dict[str,Any],
                              exposure_metrics: dict[str,Any], queue: list[dict[str,Any]],
                              metrics: dict[str,Any], alerts: list[dict[str,Any]],
                              diagnostics: dict[str,Any]) -> dict[str,Any]:
    ready=[q for q in queue if q.get("execution_policy")=="FULL_NOW"]
    delayed=[q for q in queue if q.get("execution_policy")=="DELAY"]
    reason_counts=diagnostics.get("block_reasons",{}).get("reason_counts",{})
    top_block=max(reason_counts,key=reason_counts.get) if reason_counts else "N/A"
    bullets=[
        f"VGA regime: {global_context.get('vga_environment','unknown')}",
        f"Queue depth: {len(queue)} | Ready: {len(ready)} | Delayed: {len(delayed)}",
        f"Top symbol concentration: {100*float(exposure_metrics.get('top_symbol_ratio',0)):.1f}%",
        f"Recent fill score: {metrics.get('avg_fill_score_recent',0)}",
        f"Top operational block: {top_block}",
    ]
    sections=[
        {"title":"Regime Summary","content":{k:global_context.get(k) for k in
            ["vga_environment","gamma_regime","iv_state","skew_state","term_state"]}},
        {"title":"Portfolio Posture","content":{**{k:portfolio_state.get(k) for k in ["total_campaign_basis","total_unrealized_pnl"]},**{k:exposure_metrics.get(k) for k in ["bullish_ratio","bearish_ratio","top_symbol","top_symbol_ratio"]}}},
        {"title":"Queue and Readiness","content":{"queue_depth":len(queue),
            "ready_now":len(ready),"delayed":len(delayed),"top_queue_items":queue[:5]}},
        {"title":"Alerts and Diagnostics","content":{"alert_count":len(alerts) if isinstance(alerts,list) else 0,"alerts":(alerts[:10] if isinstance(alerts,list) else []),
            "top_block_reason":top_block,
            "surface_fail_rate":diagnostics.get("gate_failures",{}).get("surface_fail_pct"),
            "timing_fail_rate":diagnostics.get("gate_failures",{}).get("timing_fail_pct")}},
    ]
    return build_report_envelope("DAILY_DESK_SUMMARY",environment,live_policy_version_id,
                                  "Daily Desk Summary",sections,bullets)
