"""
engines/alert_router.py
Generates structured alerts from engine and portfolio output.

Alert types: trade_candidate, position_action, roll_suggestion, portfolio_summary
Severity: INFO → LOW → MEDIUM → HIGH → CRITICAL
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Literal, Optional


AlertSeverity = Literal["INFO","LOW","MEDIUM","HIGH","CRITICAL"]
AlertType     = Literal["trade_candidate","position_action","roll_suggestion","portfolio_summary"]

_SEV_ORDER = {"INFO":0,"LOW":1,"MEDIUM":2,"HIGH":3,"CRITICAL":4}

_DECISION_SEV: dict[str, AlertSeverity] = {
    "STRONG":"MEDIUM","TRADABLE":"LOW","WATCHLIST":"INFO","SKIP":"INFO",
    "HOLD":"INFO","REVIEW_OR_ROLL":"HIGH",
    "CLOSE_TP":"LOW","CLOSE_STOP":"CRITICAL","CLOSE_TIME":"MEDIUM",
    "CLOSE":"HIGH","CLOSE_OR_CONVERT":"HIGH","EXIT_OR_ROLL_LONG":"HIGH",
    "CONVERT_TO_DIAGONAL":"MEDIUM","ROLL_SHORT":"LOW","ROLL_DIAGONAL_SHORT":"LOW",
    "EXIT_LONG_WINDOW":"HIGH","EXIT_STRUCTURE_BREAK":"CRITICAL","EXIT_ENVIRONMENT":"HIGH",
}

_ROLL_SEV: dict[str, AlertSeverity] = {
    "HOLD":"INFO","ROLL_OUT":"MEDIUM","ROLL_UP":"MEDIUM","ROLL_DOWN":"MEDIUM",
    "ROLL_OUT_AND_AWAY":"HIGH","CLOSE":"HIGH",
    "CONVERT_TO_DIAGONAL":"MEDIUM","EXIT_OR_ROLL_LONG":"HIGH",
}


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sf(v: Any) -> float:
    try:
        return float(str(v).replace("$","").replace(",","").strip())
    except Exception:
        return 0.0


@dataclass
class Alert:
    timestamp:  str
    symbol:     str
    alert_type: AlertType
    severity:   AlertSeverity
    title:      str
    message:    str
    action:     str   = ""
    strategy:   str   = ""
    run_id:     str   = ""
    payload:    Optional[dict] = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d.pop("payload", None)   # keep payload out of CSV row
        return d


def _alert(*, sym, atype, sev, title, msg, action="", strategy="", run_id="", payload=None):
    return Alert(timestamp=_ts(), symbol=sym, alert_type=atype, severity=sev,
                 title=title, message=msg, action=action, strategy=strategy,
                 run_id=run_id, payload=payload)

def build_candidate_alerts(engine_output: dict[str, Any], max_n: int = 5) -> list[Alert]:
    sym    = str(engine_output.get("market", {}).get("symbol", ""))
    run_id = str(engine_output.get("regime", {}).get("regime", ""))
    alerts = []
    for t in engine_output.get("candidates", [])[:max_n]:
        dec = str(t.get("decision", ""))
        sev: AlertSeverity = _DECISION_SEV.get(dec, "INFO")
        st  = str(t.get("strategy_type","")).replace("_"," ").title()
        alerts.append(_alert(
            sym=sym, atype="trade_candidate", sev=sev,
            title=f"{sym} {st} — {dec}",
            msg=(f"Score {t.get('confidence_score',0):.0f} | "
                     f"short ${t.get('short_strike','—')} long ${t.get('long_strike','—')} | "
                     f"contracts {t.get('contracts',1)}"),
            action=dec, strategy=st, run_id=run_id, payload=t,
        ))
    return alerts


def build_position_alerts(engine_output: dict[str, Any]) -> list[Alert]:
    sym    = str(engine_output.get("market", {}).get("symbol", ""))
    run_id = str(engine_output.get("regime", {}).get("regime", ""))
    alerts = []
    positions = engine_output.get("positions", {})
    all_pos = (
        positions.get("calendar_diagonal", []) +
        positions.get("credit_spreads", []) +
        positions.get("debit_spreads", [])
    )
    for pos in all_pos:
        decision = pos.get("decision", {})
        if isinstance(decision, dict):
            action = str(decision.get("action", "HOLD"))
        else:
            action = str(pos.get("management_status", "HOLD"))
        sev: AlertSeverity = _DECISION_SEV.get(action, "INFO")
        st = str(pos.get("strategy_type","")).replace("_"," ").title()
        alerts.append(_alert(
            sym=sym, atype="position_action", sev=sev,
            title=f"{sym} {st} — {action}",
            msg=(f"spot ${_sf(pos.get('live_spot')):.2f} | "
                     f"short ${pos.get('short_strike','—')} | "
                     f"DTE {pos.get('short_dte','—')}"),
            action=action, strategy=st, run_id=run_id, payload=pos,
        ))
    return alerts


def build_roll_alerts(engine_output: dict[str, Any]) -> list[Alert]:
    sym    = str(engine_output.get("market", {}).get("symbol", ""))
    run_id = str(engine_output.get("regime", {}).get("regime", ""))
    alerts = []
    for r in engine_output.get("roll_suggestions", []):
        action = str(r.get("action","HOLD"))
        urgency = str(r.get("urgency","LOW"))
        sev: AlertSeverity = "HIGH" if urgency == "HIGH" else ("MEDIUM" if urgency == "MEDIUM" else "LOW")
        alerts.append(_alert(
            sym=sym, atype="roll_suggestion", sev=sev,
            title=f"{sym} Roll — {action}",
            msg=(f"{r.get('strategy','').replace('_',' ').title()} | "
                     f"urgency {urgency} | "
                     f"target short ${r.get('target_short_strike','—')} "
                     f"DTE {r.get('target_short_dte','—')}"),
            action=action, strategy=str(r.get("strategy","")),
            run_id=run_id, payload=r,
        ))
    return alerts


def build_portfolio_alert(portfolio_output: dict[str, Any]) -> Alert:
    meta     = portfolio_output.get("portfolio_meta", {})
    selected = int(meta.get("selected_trades", 0))
    sev: AlertSeverity = "MEDIUM" if selected >= 3 else ("LOW" if selected > 0 else "INFO")
    return _alert(
        sym="PORTFOLIO", atype="portfolio_summary", sev=sev,
        title="Portfolio Engine Run",
        msg=(f"Selected {selected} trade(s), rejected {meta.get('rejected_trades',0)} | "
                 f"risk used ${_sf(meta.get('portfolio_risk_used')):,.0f}"),
        action="SUMMARY", run_id=str(meta.get("run_id","")), payload=meta,
    )


def collect_engine_alerts(engine_output: dict[str, Any]) -> list[Alert]:
    alerts: list[Alert] = []
    alerts.extend(build_candidate_alerts(engine_output))
    alerts.extend(build_position_alerts(engine_output))
    alerts.extend(build_roll_alerts(engine_output))
    return alerts


def collect_portfolio_alerts(portfolio_output: dict[str, Any]) -> list[Alert]:
    alerts: list[Alert] = [build_portfolio_alert(portfolio_output)]
    for sym_block in portfolio_output.get("symbols", []):
        alerts.extend(collect_engine_alerts(sym_block.get("engine_output", {})))
    return alerts


def filter_alerts(alerts: list[Alert], min_severity: str = "INFO") -> list[Alert]:
    min_rank = _SEV_ORDER.get(min_severity, 0)
    return [a for a in alerts if _SEV_ORDER.get(a.severity, 0) >= min_rank]
