"""
dashboard/operator_dashboard.py
Unified operations console — 15 sections in one Streamlit sidebar app.

Consolidates:
  Home (health summary + control surface)
  Bootstrap → engines/bootstrap.py
  Health Check → engines/health_check.py
  Governance Guard → engines/governance_guard.py
  Approval Queue → engines/approval_queue.py
  Config Patcher → engines/config_patcher.py
  Change Audit → engines/change_audit.py
  Release Manifest → engines/release_manifest.py
  Deployment Packet → engines/deployment_packet.py
  State Store → engines/state_store.py
  Snapshot History → engines/snapshot_manager.py
  Session Compare → engines/session_compare.py
  Analytics → backtest/metrics_reader.py
  Optimizer → engines/optimizer_report.py
  Parameter Tuner → engines/parameter_tuner.py
"""
from __future__ import annotations

import os
from typing import Any

import streamlit as st


# ─────────────────────────────────────────────
# PATH HELPERS
# ─────────────────────────────────────────────

def _cfg() -> str:
    return "config/config.yaml"

def _lp(name: str) -> str:
    return f"/tmp/options_ai_logs/{name}" if os.path.exists("/mount/src") else f"logs/{name}"

def _sp(cat: str = "") -> str:
    base = "/tmp/options_ai_snapshots" if os.path.exists("/mount/src") else "snapshots"
    return f"{base}/{cat}" if cat else base

def _state_dir() -> str:
    return "/tmp/options_ai_state" if os.path.exists("/mount/src") else "state"

def _pkt_dir() -> str:
    return "/tmp/options_ai_packets" if os.path.exists("/mount/src") else "deployment_packets"


# ─────────────────────────────────────────────
# STATUS HELPERS
# ─────────────────────────────────────────────

STATUS_COLORS = {"PASS": "#22c55e", "WARN": "#f59e0b", "FAIL": "#ef4444"}

def _sc(s: str) -> str:
    return STATUS_COLORS.get(s, "#6b7280")

def _badge(text: str, color: str = "#6b7280") -> str:
    return (f'<span style="background:{color};color:#fff;padding:3px 12px;'
            f'border-radius:20px;font-size:11px;font-weight:700">{text}</span>')


# ─────────────────────────────────────────────
# HOME
# ─────────────────────────────────────────────

def _render_home() -> None:
    from engines.health_check import run_health_check
    from engines.bootstrap import bootstrap_environment

    st.title("🛠 Operator Dashboard")
    health = run_health_check(config_path=_cfg())
    status = health["overall_status"]
    color  = _sc(status)
    s      = health["summary"]

    st.markdown(
        f'<div style="background:#0f1117;border:2px solid {color};border-radius:12px;'
        f'padding:16px;margin-bottom:16px">'
        f'<div style="display:flex;justify-content:space-between;align-items:center">'
        f'<div><div style="font-size:11px;color:#9ca3af">System Status</div>'
        f'<div style="font-size:28px;font-weight:800;color:{color}">{status}</div></div>'
        f'{_badge(status, color)}</div>'
        f'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:12px">'
        f'<div><span style="color:#22c55e">●</span> Pass <strong>{s["pass"]}</strong></div>'
        f'<div><span style="color:#f59e0b">●</span> Warn <strong>{s["warn"]}</strong></div>'
        f'<div><span style="color:#ef4444">●</span> Fail <strong>{s["fail"]}</strong></div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    recs = health.get("recommendations", [])
    if recs:
        st.markdown("**Recommended actions:**")
        for r in recs:
            st.caption(f"→ {r}")

    if status != "PASS":
        if st.button("🚀 Run Bootstrap Now", type="primary"):
            res = bootstrap_environment(config_path=_cfg())
            st.success(f"Bootstrap complete — created {res['summary']['created']} items.")
            st.rerun()

    st.divider()
    st.markdown("### Control Surface")
    sections = [
        ("🚀 Bootstrap",       "Seed folders, logs, config, state files"),
        ("🩺 Health Check",    "Validate config, files, logs, pipelines"),
        ("🛡 Governance",      "Review policy-filtered config suggestions"),
        ("✅ Approval Queue",  "Stage and approve config changes"),
        ("🛠 Config Patcher",  "Preview and apply governed config edits"),
        ("📜 Change Audit",    "Immutable log of every config mutation"),
        ("📋 Release Manifest","Release ledger with artifact references"),
        ("📦 Deployment Packet","Exportable handoff packet with zip"),
        ("💾 State Store",     "Latest engine/portfolio/alert state"),
        ("🗂 Snapshots",       "Timestamped historical snapshot archive"),
        ("🔍 Session Compare", "Delta view between two portfolio runs"),
        ("📈 Analytics",       "Engine events, selection rates, P&L"),
        ("🧠 Optimizer",       "Strategy outcomes, rejection analysis"),
        ("🎛 Parameter Tuner", "Log-driven config suggestion engine"),
    ]
    cols = st.columns(4)
    for i, (title, desc) in enumerate(sections):
        cols[i % 4].markdown(
            f'<div style="background:#0f1117;border:1px solid #374151;border-radius:10px;'
            f'padding:12px;margin-bottom:10px;min-height:80px">'
            f'<div style="font-size:14px;font-weight:700;color:#f9fafb">{title}</div>'
            f'<div style="font-size:11px;color:#6b7280;margin-top:4px">{desc}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────
# SECTION RENDERERS
# ─────────────────────────────────────────────

def _render_bootstrap() -> None:
    from engines.bootstrap import bootstrap_environment
    st.title("🚀 Bootstrap Environment")
    st.caption("Idempotent — creates missing folders, seed CSVs, state files. Never overwrites.")
    create_backup = st.checkbox("Create seed config backup", value=True)
    if st.button("▶ Run Bootstrap", type="primary"):
        result = bootstrap_environment(config_path=_cfg(), create_backup_seed=create_backup)
        c = result["summary"]["created"]
        e = result["summary"]["existing"]
        if c > 0:
            st.success(f"Created {c} items. Found {e} already present.")
        else:
            st.info(f"Already fully seeded — {e} items verified.")
        with st.expander("Details"):
            st.json(result, expanded=False)
        st.rerun()


def _render_health() -> None:
    from engines.health_check import run_health_check
    st.title("🩺 Health Check")
    health = run_health_check(config_path=_cfg())
    overall = health["overall_status"]
    color   = _sc(overall)
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f'<div style="background:#0f1117;border:2px solid {color};border-radius:10px;padding:12px;text-align:center"><div style="font-size:11px;color:#9ca3af">Overall</div><div style="font-size:22px;font-weight:700;color:{color}">{overall}</div></div>', unsafe_allow_html=True)
    c2.metric("Pass", health["summary"]["pass"])
    c3.metric("Warn", health["summary"]["warn"])
    c4.metric("Fail", health["summary"]["fail"])
    st.divider()
    for check in health["checks"]:
        col = _sc(check["status"])
        st.markdown(
            f'<div style="background:#0f1117;border:1px solid {col}44;border-radius:8px;'
            f'padding:10px;margin-bottom:6px;display:flex;justify-content:space-between">'
            f'<div><span style="font-size:13px;font-weight:600;color:#f9fafb">{check["name"]}</span>'
            f'<br><span style="font-size:11px;color:#9ca3af">{check["message"]}</span></div>'
            f'{_badge(check["status"], col)}</div>',
            unsafe_allow_html=True,
        )
    recs = health.get("recommendations", [])
    if recs:
        with st.expander("💡 Recommendations"):
            for r in recs:
                st.caption(f"• {r}")


def _render_governance() -> None:
    from engines.governance_guard import build_governance_policy_summary, evaluate_patch_payload
    from engines.parameter_tuner import tune_parameters
    from engines.config_patcher import load_config
    import pandas as pd
    st.title("🛡 Governance Guard")
    policy = build_governance_policy_summary()
    st.markdown("**Active Policy Rules**")
    st.dataframe(pd.DataFrame(policy), use_container_width=True, hide_index=True)
    st.divider()
    st.markdown("**Evaluate Current Tuner Suggestions**")
    try:
        cfg     = load_config(_cfg())
        tuning  = tune_parameters(backtest_events_path=_lp("backtest_events.csv"),
                                  execution_journal_path=_lp("execution_journal.csv"),
                                  roll_log_path=_lp("roll_suggestions.csv"))
        payload = tuning.to_dict()
        result  = evaluate_patch_payload(config=cfg, tuning_payload=payload)
        c1, c2  = st.columns(2)
        c1.metric("Approved", result["approved_count"])
        c2.metric("Rejected", result["rejected_count"])
        if result["approved"]:
            st.markdown("**Approved:**")
            st.dataframe(pd.DataFrame(result["approved"]), use_container_width=True, hide_index=True)
        if result["rejected"]:
            st.markdown("**Rejected:**")
            st.dataframe(pd.DataFrame(result["rejected"]), use_container_width=True, hide_index=True)
    except Exception as e:
        st.caption(f"Governance eval unavailable: {e}")


def _render_approval_queue() -> None:
    from engines.approval_queue import ApprovalQueue
    from engines.governance_guard import evaluate_patch_payload
    from engines.parameter_tuner import tune_parameters
    from engines.config_patcher import load_config
    st.title("✅ Approval Queue")
    queue = ApprovalQueue(path=_lp("approval_queue.csv"))
    c1, c2 = st.columns(2)
    c1.metric("Pending",  len(queue.pending_requests()))
    c2.metric("Approved", len(queue.approved_requests()))

    if st.button("🔄 Stage Governance-Approved Suggestions"):
        try:
            cfg     = load_config(_cfg())
            tuning  = tune_parameters(backtest_events_path=_lp("backtest_events.csv"),
                                      execution_journal_path=_lp("execution_journal.csv"),
                                      roll_log_path=_lp("roll_suggestions.csv"))
            gov     = evaluate_patch_payload(config=cfg, tuning_payload=tuning.to_dict())
            created = queue.create_many_from_governed_suggestions(governance_payload=gov, approved_only=True)
            st.success(f"Staged {len(created)} request(s).")
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

    pending = queue.pending_requests()
    if pending:
        st.markdown("**Pending:**")
        for item in pending:
            with st.container():
                cl, cr = st.columns([3,1])
                cl.markdown(f'`{item["parameter"]}` `{item["current_value"]}` → `{item["requested_value"]}`')
                cl.caption(item.get("rationale",""))
                rev = cr.text_input("Reviewer", key=f"rev_{item['request_id']}", label_visibility="collapsed", placeholder="Reviewer")
                ca, cb = cr.columns(2)
                if ca.button("✓", key=f"ap_{item['request_id']}"):
                    queue.approve(item["request_id"], reviewer=rev)
                    st.rerun()
                if cb.button("✗", key=f"rj_{item['request_id']}"):
                    queue.reject(item["request_id"], reviewer=rev)
                    st.rerun()
                st.divider()

    approved = queue.approved_requests()
    if approved:
        st.markdown("**Approved (ready to apply):**")
        for a in approved:
            st.markdown(f"✅ `{a['parameter']}` → `{a['requested_value']}` by `{a.get('reviewer','—')}`")


def _render_config_patcher() -> None:
    from engines.parameter_tuner import tune_parameters
    from engines.config_patcher import (
        preview_config_patch, apply_config_patch,
        build_tuning_payload_from_queue_requests,
    )
    from engines.approval_queue import ApprovalQueue
    st.title("🛠 Config Patcher")
    tuning  = tune_parameters(backtest_events_path=_lp("backtest_events.csv"),
                              execution_journal_path=_lp("execution_journal.csv"),
                              roll_log_path=_lp("roll_suggestions.csv"))
    payload = tuning.to_dict()
    sugs    = payload.get("suggestions", [])

    if not sugs:
        st.info("No tuner suggestions yet — run the engine with logging enabled to generate data.")
        return

    labels     = [f'{s["parameter"]} → {s["suggested_value"]} ({int(s.get("confidence",0)*100)}%)' for s in sugs]
    params_map = {l: s["parameter"] for l, s in zip(labels, sugs)}
    selected   = st.multiselect("Parameters to patch", labels, default=labels)
    sel_params = [params_map[l] for l in selected]
    min_conf   = st.slider("Min confidence", 0.0, 1.0, 0.65, 0.05)
    enforce_gov = st.checkbox("Enforce governance guard", value=True)
    reviewer   = st.text_input("Reviewer (for audit log)", placeholder="e.g. Christian")
    backup_dir = "/tmp/options_ai_config_backups" if os.path.exists("/mount/src") else "config_backups"

    c1, c2 = st.columns(2)
    with c1:
        if st.button("👁 Preview"):
            r = preview_config_patch(config_path=_cfg(), tuning_payload=payload,
                                     include_parameters=sel_params, min_confidence=min_conf,
                                     enforce_governance=enforce_gov)
            st.json(r.to_dict(), expanded=False)
    with c2:
        if st.button("✅ Apply Patch", type="primary"):
            r = apply_config_patch(config_path=_cfg(), tuning_payload=payload,
                                   include_parameters=sel_params, min_confidence=min_conf,
                                   make_backup=True, backup_dir=backup_dir,
                                   enforce_governance=enforce_gov, reviewer=reviewer,
                                   audit_log=True, audit_path=_lp("change_audit.csv"))
            if r.applied:
                st.success(f"Applied. Notes: {r.notes}")
            else:
                st.info(f"No changes. Notes: {r.notes}")
            st.json(r.to_dict(), expanded=False)

    st.divider()
    st.markdown("**Apply From Approval Queue**")
    queue    = ApprovalQueue(path=_lp("approval_queue.csv"))
    approved = queue.approved_requests()
    if approved:
        import pandas as pd
        st.dataframe(pd.DataFrame(approved), use_container_width=True, hide_index=True)
        if st.button("⚡ Apply Approved Queue", type="primary"):
            qp = build_tuning_payload_from_queue_requests(approved)
            r  = apply_config_patch(config_path=_cfg(), tuning_payload=qp,
                                    include_parameters=[x["parameter"] for x in approved],
                                    min_confidence=0.0, make_backup=True, backup_dir=backup_dir,
                                    enforce_governance=True, reviewer=reviewer,
                                    audit_log=True, audit_path=_lp("change_audit.csv"),
                                    source="queue")
            if r.applied:
                for req in approved:
                    queue.mark_applied(req["request_id"], reviewer=reviewer or "system")
                st.success(f"Applied. Notes: {r.notes}")
            else:
                st.info(f"No changes. Notes: {r.notes}")
    else:
        st.caption("No approved queue requests.")


def _render_change_audit() -> None:
    from engines.change_audit import ChangeAudit
    import pandas as pd
    st.title("📜 Change Audit")
    audit   = ChangeAudit(path=_lp("change_audit.csv"))
    summary = audit.summary()
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Changes",  summary.get("total_changes",0))
    c2.metric("Last Change",    str(summary.get("last_change","—"))[:19])
    c3.metric("Reviewers",      len(summary.get("reviewers",[])))
    rows = audit.load()
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        audit_path = _lp("change_audit.csv")
        if os.path.exists(audit_path):
            st.download_button("⬇ Download", open(audit_path,"rb").read(),
                               "change_audit.csv","text/csv", use_container_width=True)
    else:
        st.caption("No audit entries yet.")


def _render_release_manifest() -> None:
    from engines.release_manifest import ReleaseManifest
    import pandas as pd
    st.title("📋 Release Manifest")
    rm   = ReleaseManifest(path=_lp("release_manifest.csv"))
    rows = rm.list_releases(limit=50)
    if not rows:
        st.info("No releases logged yet.")
        return
    cols_to_show = [c for c in ["created_at","release_type","release_name",
                                 "portfolio_run_id","health_status","notes"] if c in rows[0]]
    st.dataframe(pd.DataFrame(rows)[cols_to_show], use_container_width=True, hide_index=True)
    labels = [f"{r['created_at'][:19]} · {r['release_type']} · {r['release_name']}" for r in rows]
    sel    = st.selectbox("Detail", range(len(labels)), format_func=lambda i: labels[i])
    with st.expander("Release detail"):
        st.json(rm.get_release(rows[sel]["release_id"]), expanded=False)


def _render_deployment_packet() -> None:
    from engines.deployment_packet import DeploymentPacketBuilder
    st.title("📦 Deployment Packet")
    name        = st.text_input("Packet name", "release_packet")
    inc_zip     = st.checkbox("Create zip", value=True)
    inc_logs    = st.checkbox("Include full governance logs", value=False)
    if st.button("📦 Build Packet", type="primary"):
        builder = DeploymentPacketBuilder(
            output_dir=_pkt_dir(), logs_dir="logs", state_dir=_state_dir(),
            snapshots_dir=_sp(), config_path=_cfg(),
        )
        with st.spinner("Building..."):
            result = builder.build_packet(packet_name=name, include_zip=inc_zip,
                                          include_full_logs=inc_logs)
        st.success(f"Built: `{result['packet_id']}`")
        if result.get("zip_path") and os.path.exists(result["zip_path"]):
            st.download_button("⬇ Download .zip", open(result["zip_path"],"rb").read(),
                               f"{name}.zip","application/zip", use_container_width=True)
        with st.expander("Manifest"):
            st.json(result["deployment_manifest"], expanded=False)


def _render_state_store() -> None:
    from engines.state_store import StateStore
    st.title("💾 State Store")
    store = StateStore(base_dir=_state_dir())
    for label, fn in [("Portfolio", "load_portfolio_state"), ("Engine", "load_engine_state"),
                      ("Alerts", "load_alerts_state")]:
        data = getattr(store, fn)()
        ts   = data.get("saved_at","never")[:19] if data else "never"
        with st.expander(f"{label} State — last saved {ts}"):
            st.json(data or {}, expanded=False)


def _render_snapshots() -> None:
    from engines.snapshot_manager import SnapshotManager
    import pandas as pd
    st.title("🗂 Snapshot History")
    mgr   = SnapshotManager(base_dir=_sp())
    cat   = st.selectbox("Category", ["all","portfolio","engine","blotter","alerts"])
    items = mgr.list_snapshots(category=None if cat=="all" else cat, limit=100)
    if not items:
        st.info("No snapshots yet.")
        return
    st.markdown(f"**{len(items)} snapshot(s)**")
    df = pd.DataFrame(items)[["category","filename","mtime"]]
    df["mtime"] = pd.to_datetime(df["mtime"], unit="s").dt.strftime("%Y-%m-%d %H:%M")
    st.dataframe(df, use_container_width=True, hide_index=True)
    labels = [f"{i['category']} · {i['filename']}" for i in items]
    sel    = st.selectbox("View snapshot", range(len(labels)), format_func=lambda i: labels[i])
    with st.expander("Snapshot content"):
        st.json(mgr.load_snapshot(items[sel]["path"]), expanded=False)


def _render_session_compare() -> None:
    from engines.snapshot_manager import SnapshotManager
    from engines.session_compare import compare_portfolio_snapshots
    st.title("🔍 Session Compare")
    mgr   = SnapshotManager(base_dir=_sp())
    items = mgr.list_snapshots(category="portfolio", limit=20)
    if len(items) < 2:
        st.info("Need at least 2 portfolio snapshots.")
        return
    labels = [i["filename"] for i in items]
    c1, c2 = st.columns(2)
    with c1:
        old_i = st.selectbox("Older", range(len(labels)), index=min(1,len(labels)-1), format_func=lambda i: labels[i])
    with c2:
        new_i = st.selectbox("Newer", range(len(labels)), index=0, format_func=lambda i: labels[i])
    cmp   = compare_portfolio_snapshots(mgr.load_snapshot(items[old_i]["path"]),
                                        mgr.load_snapshot(items[new_i]["path"]))
    st.markdown(f"**Old:** `{cmp['old_run_id']}` → **New:** `{cmp['new_run_id']}`")
    import pandas as pd
    md = cmp.get("meta_delta",{})
    if md:
        cols = st.columns(min(len(md),4))
        for i, (field, vals) in enumerate(md.items()):
            delta = vals.get("delta",0)
            cols[i%4].metric(field.replace("_"," ").title(), vals.get("new","—"),
                              delta=f"{delta:+.2f}" if delta else None)
    for label, key in [("Selected Trades","selected_trades"),("Roll Suggestions","roll_suggestions")]:
        data = cmp.get(key,{})
        n_add = len(data.get("added",[])); n_rem = len(data.get("removed",[])); n_chg = len(data.get("changed",[]))
        if any([n_add,n_rem,n_chg]):
            with st.expander(f"{label} — +{n_add} -{n_rem} ~{n_chg}"):
                if data.get("added"):   st.markdown("**Added:**");   st.json(data["added"][:5])
                if data.get("changed"): st.markdown("**Changed:**"); st.json(data["changed"][:5])


def _render_analytics() -> None:
    import pandas as pd
    from backtest.metrics_reader import (load_events, load_runs, summary_stats,
                                         by_symbol, by_regime, rejection_reasons,
                                         by_strategy, selection_rate_by_regime)
    st.title("📈 Analytics")
    df_ev = load_events(_lp("backtest_events.csv"))
    df_ru = load_runs(_lp("backtest_runs.csv"))
    if df_ev.empty:
        st.info("No analytics data yet. Run the engine with `log_backtest_events=True`.")
        return
    stats = summary_stats(df_ev)
    cols  = st.columns(8)
    labels = [("Events",stats["total_events"]),("Ranked",stats["ranked_trades"]),
              ("Selected",stats["selected_trades"]),("Rejected",stats["rejected_trades"]),
              ("Actions",stats["position_actions"]),("Avg Ranked",stats["avg_ranked_score"]),
              ("Avg Selected",stats["avg_selected_score"]),("Est P&L",f"${stats['estimated_position_pnl']:.2f}")]
    for i,(l,v) in enumerate(labels): cols[i].metric(l,v)
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**By Symbol**");  st.dataframe(by_symbol(df_ev), use_container_width=True, hide_index=True)
        st.markdown("**By Regime**");  st.dataframe(by_regime(df_ev), use_container_width=True, hide_index=True)
    with c2:
        st.markdown("**Rejections**"); st.dataframe(rejection_reasons(df_ev), use_container_width=True, hide_index=True)
        st.markdown("**Selection Rate**"); st.dataframe(selection_rate_by_regime(df_ev), use_container_width=True, hide_index=True)
    if not df_ru.empty:
        st.divider(); st.markdown("**Run History**")
        st.dataframe(df_ru.tail(20), use_container_width=True, hide_index=True)
    ev_path = _lp("backtest_events.csv")
    if os.path.exists(ev_path):
        st.download_button("⬇ backtest_events.csv", open(ev_path,"rb").read(),
                           "backtest_events.csv","text/csv", use_container_width=True)


def _render_optimizer() -> None:
    from engines.optimizer_report import build_optimizer_report
    st.title("🧠 Optimizer Report")
    report  = build_optimizer_report(backtest_events_path=_lp("backtest_events.csv"),
                                     execution_journal_path=_lp("execution_journal.csv"),
                                     roll_log_path=_lp("roll_suggestions.csv"),
                                     snapshots_dir=_sp())
    summary = report["summary"]
    best_s  = summary.get("best_strategy",{})
    top_r   = summary.get("dominant_rejection_reason",{})
    top_sym = summary.get("best_symbol_candidate",{})
    c1, c2, c3 = st.columns(3)
    c1.metric("Best Strategy",    best_s.get("strategy","—"),
              delta=f'expectancy ${best_s.get("expectancy",0):.2f}' if best_s else None)
    c2.metric("Top Rejection",    top_r.get("reject_reason", top_r.get("reason","—")),
              delta=f'{top_r.get("count",0)} occurrences' if top_r else None)
    c3.metric("Best Symbol",      top_sym.get("symbol","—"),
              delta=top_sym.get("allocation_action","—") if top_sym else None)
    st.divider()
    tabs = st.tabs(["Strategy","Rejections","Roll Patterns","Allocation","Snapshots"])
    for tab, df in zip(tabs, [report["strategy_outcomes"],report["rejection_reasons"],
                               report["roll_actions"],report["symbol_allocation"],
                               report["snapshot_changes"]]):
        with tab:
            if df is None or df.empty:
                st.caption("No data yet.")
            else:
                st.dataframe(df, use_container_width=True, hide_index=True)
    tuning = report.get("parameter_tuning",{})
    if tuning.get("suggestions"):
        with st.expander("Parameter Tuning Handoff"):
            st.json(tuning, expanded=False)


def _render_parameter_tuner() -> None:
    from engines.parameter_tuner import tune_parameters
    st.title("🎛 Parameter Tuner")
    tuning  = tune_parameters(backtest_events_path=_lp("backtest_events.csv"),
                              execution_journal_path=_lp("execution_journal.csv"),
                              roll_log_path=_lp("roll_suggestions.csv"))
    payload = tuning.to_dict()
    summary = payload["summary"]
    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("Sel/Rej Ratio",    summary.get("selected_rejected_ratio","—"))
    c2.metric("Top Rejection",    summary.get("top_rejection_reason","—") or "—")
    c3.metric("Top Roll Action",  summary.get("top_roll_action","—") or "—")
    c4.metric("Strategies w/ Data", summary.get("strategies_with_data",0))
    c5.metric("Symbols Active",   summary.get("symbols_active",0))
    sugs = payload.get("suggestions",[])
    if not sugs:
        st.info("No suggestions yet — more engine runs needed.")
        return
    for s in sugs:
        conf = float(s.get("confidence",0))
        col  = "#22c55e" if conf>=0.70 else ("#f59e0b" if conf>=0.55 else "#6b7280")
        st.markdown(
            f'<div style="background:#0f1117;border:1px solid {col}33;border-radius:10px;'
            f'padding:12px;margin-bottom:8px">'
            f'<div style="display:flex;justify-content:space-between">'
            f'<div><span style="font-size:11px;color:#9ca3af">{s["parameter"]}</span><br>'
            f'<span style="font-size:16px;font-weight:700;color:{col}">{s["direction"].upper()}</span></div>'
            f'<div style="text-align:right"><span style="font-size:11px;color:#9ca3af">Confidence</span><br>'
            f'<span style="font-size:16px;font-weight:700;color:{col}">{conf:.0%}</span></div></div>'
            f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:8px">'
            f'<div><span style="font-size:10px;color:#6b7280">Current</span><br>'
            f'<span style="color:#e5e7eb">{s["current_value"]}</span></div>'
            f'<div><span style="font-size:10px;color:#6b7280">Suggested</span><br>'
            f'<span style="color:#e5e7eb">{s["suggested_value"]}</span></div></div>'
            f'<div style="margin-top:6px;font-size:11px;color:#9ca3af">{s.get("rationale","")}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────
# MAIN ENTRY
# ─────────────────────────────────────────────


def _render_live_data() -> None:
    """📡 Live Data — run engine against real provider data."""
    import os
    from providers.provider_factory import build_provider
    from providers.runtime_data_service import RuntimeDataService

    st.title("📡 Live Data Runtime")

    provider_type = st.radio(
        "Provider",
        ["mock","massive","csv"],
        format_func=lambda p: {"mock":"🧪 Mock","massive":"📈 Massive/Polygon","csv":"📂 CSV files"}[p],
        horizontal=True,
        key="op_live_provider",
    )
    kwargs: dict = {}
    if provider_type == "massive":
        key = st.text_input("MASSIVE_API_KEY", os.getenv("MASSIVE_API_KEY",""), type="password", key="op_live_key")
        if key: kwargs["api_key"] = key
    elif provider_type == "csv":
        kwargs["reports_dir"]    = st.text_input("Reports dir", "data/reports", key="op_live_rdir")
        kwargs["chains_dir"]     = st.text_input("Chains dir",  "data/chains",  key="op_live_cdir")
        kwargs["positions_path"] = st.text_input("Positions",   "data/positions/open_positions.csv", key="op_live_pos")

    symbols_raw = st.text_input("Symbols", "SPY", key="op_live_sym")
    symbols     = [s.strip().upper() for s in symbols_raw.split(",") if s.strip()]
    col1, col2  = st.columns(2)
    log_ev      = col1.checkbox("Log events",  key="op_live_lev")
    persist     = col2.checkbox("Persist state", key="op_live_ps")

    if not st.button("▶ Run", type="primary", key="op_live_run"):
        return

    try:
        svc = RuntimeDataService(build_provider(provider_type, **kwargs))
    except Exception as e:
        st.error(f"Provider init failed: {e}"); return

    with st.spinner(f"Running via {svc.provider_name}..."):
        try:
            out = svc.run_portfolio(symbols, log_backtest_events=log_ev,
                                    persist_state=persist, snapshot_history=persist)
        except Exception as e:
            st.error(f"Engine error: {e}"); st.exception(e); return

    meta  = out["portfolio_meta"]
    alloc = out["allocation"]
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Symbols",  meta["symbols_processed"])
    c2.metric("Ranked",   meta["total_ranked_trades"])
    c3.metric("Selected", meta["selected_trades"])
    c4.metric("Used Risk", f"${alloc['used_risk_budget']:,.0f}")
    for b in out["symbols"]:
        eng = b["engine_output"]
        st.markdown(f"**{b['symbol']}** `{eng.get('vga','?')}` "
                    f"spot=${eng['market'].get('spot_price',0):.2f} "
                    f"EM±${eng['derived'].get('expected_move',0):.2f} "
                    f"candidates={len(eng.get('candidates',[]))}")
        for c in eng.get("candidates",[])[:3]:
            st.caption(f"  • {c.get('strategy_type','?')} score={c.get('confidence_score',0):.0f} {c.get('decision','?')}")
    with st.expander("Raw output"):
        st.json(meta)


PAGES = {
    "🏠 Home":               _render_home,
    "🚀 Bootstrap":          _render_bootstrap,
    "🩺 Health Check":       _render_health,
    "🛡 Governance":         _render_governance,
    "✅ Approval Queue":     _render_approval_queue,
    "🛠 Config Patcher":     _render_config_patcher,
    "📜 Change Audit":       _render_change_audit,
    "📋 Release Manifest":   _render_release_manifest,
    "📦 Deployment Packet":  _render_deployment_packet,
    "💾 State Store":        _render_state_store,
    "🗂 Snapshots":          _render_snapshots,
    "🔍 Session Compare":    _render_session_compare,
    "📈 Analytics":          _render_analytics,
    "🧠 Optimizer":          _render_optimizer,
    "🎛 Parameter Tuner":    _render_parameter_tuner,
    "📡 Live Data":          _render_live_data,
}


def render_operator_dashboard() -> None:
    """
    Standalone multi-page Streamlit app.
    Run with: streamlit run dashboard/operator_dashboard_app.py
    """
    st.set_page_config(page_title="Operator Dashboard", layout="wide", initial_sidebar_state="expanded")

    with st.sidebar:
        st.markdown("### 🛠 Operator")
        st.caption("Options AI — Control Plane")
        st.divider()
        page = st.radio("Section", list(PAGES.keys()), label_visibility="collapsed")
        st.divider()
        st.caption("v22 · Options AI Assistant")

    PAGES[page]()
