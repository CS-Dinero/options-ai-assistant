"""
engines/session_compare.py
Compares two portfolio snapshots and returns structured deltas.

compare_portfolio_snapshots(old, new) → {
    old_run_id, new_run_id,
    meta_delta,
    selected_trades: {added, removed, changed},
    ranked_trades:   {added, removed, changed},
    alerts:          {added, removed},
    roll_suggestions:{added, removed, changed},
}
"""
from __future__ import annotations
from typing import Any


def _sf(v: Any, d: float = 0.0) -> float:
    try:
        return float(str(v).replace("$","").replace(",","").strip()) if v not in (None,"","—") else d
    except Exception:
        return d


def _trade_key(t: dict) -> tuple:
    return (str(t.get("symbol","")), str(t.get("strategy_type", t.get("strategy",""))),
            str(t.get("short_strike","")), str(t.get("long_strike","")),
            str(t.get("short_dte","")), str(t.get("long_dte","")))


def _alert_key(a: dict) -> tuple:
    return (str(a.get("symbol","")), str(a.get("alert_type","")),
            str(a.get("strategy","")), str(a.get("action","")))


def _roll_key(r: dict) -> tuple:
    return (str(r.get("symbol","")), str(r.get("strategy","")),
            str(r.get("action","")), str(r.get("short_strike","")))


def _idx(rows: list, key_fn) -> dict:
    return {key_fn(r): r for r in rows}


def _compare_trades(old: list, new: list) -> dict:
    om, nm = _idx(old, _trade_key), _idx(new, _trade_key)
    ok, nk = set(om), set(nm)
    changed = []
    for k in ok & nk:
        o, n = om[k], nm[k]
        s_old = _sf(o.get("confidence_score", o.get("score")))
        s_new = _sf(n.get("confidence_score", n.get("score")))
        d_old = str(o.get("decision",""))
        d_new = str(n.get("decision",""))
        if round(s_old,1) != round(s_new,1) or d_old != d_new:
            changed.append({"symbol": n.get("symbol",""),
                             "strategy": n.get("strategy_type", n.get("strategy","")),
                             "old_score": s_old, "new_score": s_new,
                             "delta": round(s_new-s_old,2),
                             "old_decision": d_old, "new_decision": d_new})
    return {"added":   [nm[k] for k in sorted(nk-ok)],
            "removed": [om[k] for k in sorted(ok-nk)],
            "changed": changed}


def _compare_alerts(old: list, new: list) -> dict:
    om, nm = _idx(old, _alert_key), _idx(new, _alert_key)
    ok, nk = set(om), set(nm)
    return {"added":   [nm[k] for k in sorted(nk-ok)],
            "removed": [om[k] for k in sorted(ok-nk)]}


def _compare_rolls(old: list, new: list) -> dict:
    om, nm = _idx(old, _roll_key), _idx(new, _roll_key)
    ok, nk = set(om), set(nm)
    changed = []
    for k in ok & nk:
        o, n = om[k], nm[k]
        if o.get("urgency") != n.get("urgency") or o.get("target_short_strike") != n.get("target_short_strike"):
            changed.append({"symbol": n.get("symbol",""), "strategy": n.get("strategy",""),
                             "old_urgency": o.get("urgency"), "new_urgency": n.get("urgency"),
                             "old_target": o.get("target_short_strike"),
                             "new_target": n.get("target_short_strike")})
    return {"added":   [nm[k] for k in sorted(nk-ok)],
            "removed": [om[k] for k in sorted(ok-nk)],
            "changed": changed}


def _meta_delta(old: dict, new: dict) -> dict:
    fields = ["selected_trades","rejected_trades","portfolio_risk_budget",
              "portfolio_risk_used","portfolio_risk_remaining","total_ranked_trades"]
    return {f: {"old": old.get(f,0), "new": new.get(f,0),
                "delta": round(_sf(new.get(f,0)) - _sf(old.get(f,0)), 2)}
            for f in fields}


def _extract(snap: dict) -> dict:
    for k in ("portfolio_output", "payload"):
        if k in snap:
            return snap[k]
    return snap


def _flatten_ranked(output: dict) -> list:
    rows = []
    for b in output.get("symbols", []):
        sym = b.get("symbol","")
        for t in b.get("engine_output",{}).get("candidates",[]):
            r = dict(t); r.setdefault("symbol", sym); rows.append(r)
    return rows


def _flatten_rolls(output: dict) -> list:
    return output.get("roll_suggestions", [])


def compare_portfolio_snapshots(old_snap: dict, new_snap: dict) -> dict:
    old = _extract(old_snap)
    new = _extract(new_snap)

    return {
        "old_run_id":       old.get("portfolio_meta",{}).get("run_id",""),
        "new_run_id":       new.get("portfolio_meta",{}).get("run_id",""),
        "meta_delta":       _meta_delta(old.get("portfolio_meta",{}), new.get("portfolio_meta",{})),
        "selected_trades":  _compare_trades(
            old.get("allocation",{}).get("selected_trades",[]),
            new.get("allocation",{}).get("selected_trades",[])),
        "ranked_trades":    _compare_trades(_flatten_ranked(old), _flatten_ranked(new)),
        "alerts":           _compare_alerts(old.get("alerts",[]), new.get("alerts",[])),
        "roll_suggestions": _compare_rolls(_flatten_rolls(old), _flatten_rolls(new)),
    }
