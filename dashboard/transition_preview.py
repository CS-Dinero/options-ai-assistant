"""
dashboard/transition_preview.py
Read-only Transition Preview panel.

render_transition_preview(position_row)      — full preview
render_transition_orders(position_row, ticket) — close/open order sequence
"""
from __future__ import annotations

import streamlit as st
from typing import Any


ACTION_COLORS: dict[str, str] = {
    "FLIP_TO_CALL_DIAGONAL":      "#1d4ed8",
    "FLIP_TO_PUT_DIAGONAL":       "#dc2626",
    "CONVERT_TO_BULL_PUT_SPREAD": "#16a34a",
    "CONVERT_TO_BEAR_CALL_SPREAD":"#f97316",
    "HOLD_CURRENT_HARVEST":       "#6b7280",
    "EXIT_AND_BANK":              "#ca8a04",
}

ACTION_EMOJIS: dict[str, str] = {
    "FLIP_TO_CALL_DIAGONAL":      "🔵",
    "FLIP_TO_PUT_DIAGONAL":       "🔴",
    "CONVERT_TO_BULL_PUT_SPREAD": "🟢",
    "CONVERT_TO_BEAR_CALL_SPREAD":"🟠",
    "HOLD_CURRENT_HARVEST":       "⬜",
    "EXIT_AND_BANK":              "🟡",
}

_sf = lambda v, d=0.0: (float(v) if v not in (None,"","—") else d)


def _badge(text: str, color: str, text_color: str = "#fff") -> str:
    return (f'<span style="background:{color};color:{text_color};padding:3px 14px;'
            f'border-radius:20px;font-size:11px;font-weight:700">{text}</span>')


def _score_bar(score: float, label: str = "") -> None:
    color = "#22c55e" if score >= 70 else "#f59e0b" if score >= 50 else "#ef4444"
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:8px;margin:2px 0">'
        f'<span style="font-size:11px;color:#9ca3af;width:120px">{label}</span>'
        f'<div style="flex:1;background:#1f2937;border-radius:4px;height:8px">'
        f'<div style="width:{min(score,100):.0f}%;background:{color};height:8px;border-radius:4px"></div>'
        f'</div>'
        f'<span style="font-size:11px;color:#e5e7eb;width:35px">{score:.0f}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _score_bar(score: float, label: str = "") -> None:
    color = "#22c55e" if score >= 70 else "#f59e0b" if score >= 50 else "#ef4444"
    import streamlit as _st2
    _st2.markdown(
        f'<div style="display:flex;align-items:center;gap:8px;margin:2px 0">'
        f'<span style="font-size:11px;color:#9ca3af;width:130px">{label}</span>'
        f'<div style="flex:1;background:#1f2937;border-radius:4px;height:8px">'
        f'<div style="width:{min(score,100):.0f}%;background:{color};height:8px;border-radius:4px"></div>'
        f'</div><span style="font-size:11px;color:#e5e7eb;width:35px">{score:.0f}</span></div>',
        unsafe_allow_html=True)

def render_transition_preview(position_row: dict[str, Any]) -> None:
    """Full transition preview panel — sections A through D."""
    action  = str(position_row.get("transition_action","HOLD_CURRENT_HARVEST"))
    color   = ACTION_COLORS.get(action, "#6b7280")
    emoji   = ACTION_EMOJIS.get(action, "⬜")
    credit  = _sf(position_row.get("transition_net_credit"))
    frs     = _sf(position_row.get("transition_future_roll_score"))
    comp    = _sf(position_row.get("transition_structure_score"))
    approved = bool(position_row.get("transition_is_credit_approved"))

    # Header
    st.markdown(
        f'<div style="background:#0f1117;border:2px solid {color}44;border-radius:12px;padding:14px">'
        f'<div style="display:flex;justify-content:space-between;align-items:center">'
        f'<span style="font-size:15px;font-weight:700">{emoji} Transition Preview</span>'
        f'{_badge(action.replace("_"," "), color)}'
        f'</div></div>',
        unsafe_allow_html=True,
    )
    st.caption(
        f'{"✅ Approved" if approved else "❌ Not approved"} | '
        f'Credit ${credit:.2f}/share | '
        f'Future roll score {frs:.0f} | '
        f'Composite {comp:.0f}'
    )

    # ── A. Current structure ──────────────────────────────────────────────────
    st.markdown("**A — Current Structure**")
    a1, a2, a3, a4, a5 = st.columns(5)
    a1.metric("Symbol",   position_row.get("symbol","—"))
    a2.metric("Strategy", str(position_row.get("strategy_type","—")).replace("_"," ").title())
    a3.metric("Net Liq",  f'${_sf(position_row.get("net_liq")):.0f}')
    a4.metric("Short DTE",position_row.get("short_dte","—"))
    a5.metric("Long DTE", position_row.get("long_dte","—"))

    # ── B. Proposed transition ────────────────────────────────────────────────
    st.divider()
    st.markdown("**B — Proposed Transition**")
    b1, b2, b3 = st.columns(3)

    new_struct = position_row.get("transition_new_structure_type","—")
    new_short  = position_row.get("transition_new_short_leg") or {}
    new_long   = position_row.get("transition_new_long_leg")  or {}

    b1.metric("Target Structure", str(new_struct).replace("_"," ").title())
    b2.metric("Net Credit / share", f"${credit:.2f}",
              delta="✅ above minimum" if approved else "❌ below minimum",
              delta_color="normal" if approved else "inverse")
    b3.metric("Future Roll Score", f"{frs:.0f}/100",
              delta="✅ harvestable" if frs >= 65 else "⚠️ marginal",
              delta_color="normal" if frs >= 65 else "inverse")

    if new_short:
        ns1, ns2, ns3, ns4 = st.columns(4)
        ns1.metric("New Short Strike", f'${_sf(new_short.get("strike")):.1f}')
        ns2.metric("New Short Expiry", str(new_short.get("expiry") or new_short.get("expiration","—")))
        ns3.metric("New Short Delta",  f'{abs(_sf(new_short.get("delta"))):.2f}')
        ns4.metric("New Short Mid",    f'${_sf(new_short.get("mid") or new_short.get("bid")):.2f}')

    # ── C. Score breakdown ────────────────────────────────────────────────────
    st.divider()
    st.markdown("**C — Score Breakdown**")
    _score_bar(_sf(position_row.get("_tc_credit_score",   comp)), "Credit")
    _score_bar(_sf(position_row.get("_tc_skew_score",     0.0)), "Skew Edge")
    _score_bar(frs,                                               "Future Rollability")
    _score_bar(_sf(position_row.get("_tc_structure_score",comp)), "Structure Fit")
    _score_bar(_sf(position_row.get("_tc_liquidity_score",0.0)), "Liquidity")
    _score_bar(_sf(position_row.get("_tc_assignment_score",0.0)),"Assignment Safety")

    # ── D. Why approved ───────────────────────────────────────────────────────
    st.divider()
    st.markdown("**D — Rationale**")
    for item in (position_row.get("transition_why") or ["No reasons provided."]):
        st.caption(f"→ {item}")

    side_edge = position_row.get("transition_side_edge")
    if side_edge:
        st.info(f"📐 Skew edge: **{side_edge}** side currently richer — "
                f"flip harvests premium from the richer IV surface.")

    # ── E. Campaign economics ────────────────────────────────────────────────
    st.divider()
    st.markdown("**E — Campaign Economics**")
    e1,e2,e3,e4 = st.columns(4)
    e1.metric("Basis Before",   f'${_sf(position_row.get("transition_campaign_net_basis_before")):.2f}')
    e2.metric("Basis After",    f'${_sf(position_row.get("transition_campaign_net_basis_after")):.2f}',
              delta=f'-${_sf(position_row.get("transition_basis_reduction")):.2f}' if _sf(position_row.get("transition_basis_reduction"))>0 else None)
    e3.metric("Recovered %",    f'{_sf(position_row.get("transition_recovered_pct_after")):.1f}%')
    e4.metric("Campaign Score", f'{_sf(position_row.get("transition_campaign_improvement_score")):.0f}')

    # ── F. Path robustness ────────────────────────────────────────────────────
    st.divider()
    st.markdown("**F — Path Robustness**")
    f1,f2,f3 = st.columns(3)
    avg_p  = _sf(position_row.get("transition_avg_path_score"))
    wst_p  = _sf(position_row.get("transition_worst_path_score"))
    bst_p  = _sf(position_row.get("transition_best_path_score"))
    robust = bool(position_row.get("transition_path_robust"))
    f1.metric("Avg Path Score",   f"{avg_p:.0f}")
    f2.metric("Worst Path Score", f"{wst_p:.0f}")
    f3.metric("Best Path Score",  f"{bst_p:.0f}")
    st.caption(f"{'✅ Robust across tested paths' if robust else '⚠️ Path fragility detected'}")
    if avg_p>=70 and wst_p>=50: st.info("Transition holds up well across flat, favorable, and adverse paths.")
    elif wst_p<45: st.warning("Fragile under adverse scenario — confirm before executing.")
    if bst_p-wst_p>30: st.caption("⚠️ High spread between best/worst path — scenario-concentrated.")

    sc = position_row.get("transition_scenario_results",[])
    if sc:
        with st.expander(f"Scenario table ({len(sc)} paths)"):
            import pandas as pd
            st.dataframe(pd.DataFrame([{
                "Scenario":    r["label"], "Spot":r["spot_scenario"],
                "Decay":       f'{r["short_decay_score"]:.0f}',
                "Rollability": f'{r["rollability_score"]:.0f}',
                "Assign Risk": f'{r["assignment_risk_score"]:.0f}',
                "Resilience":  f'{r["resilience_score"]:.0f}',
                "Path Score":  f'{r["path_score"]:.0f}',
            } for r in sc]), use_container_width=True, hide_index=True)

    # ── G. Rebuild decision ───────────────────────────────────────────────────
    rb_class = str(position_row.get("transition_rebuild_class","KEEP_LONG"))
    if rb_class == "REPLACE_LONG":
        st.divider()
        st.markdown("**G — Rebuild Decision: REPLACE LONG**")
        st.caption("The optimizer found a materially better long leg. Both legs will change.")
        old_long = position_row.get("long_leg") or {}
        new_long = position_row.get("transition_new_long_leg") or {}
        if old_long or new_long:
            g1,g2 = st.columns(2)
            g1.metric("Old Long", f'${_sf(old_long.get("strike")):.0f} '
                       f'{str(old_long.get("expiry") or old_long.get("expiration",""))[:10]}')
            g2.metric("New Long", f'${_sf(new_long.get("strike")):.0f} '
                       f'{str(new_long.get("expiry") or new_long.get("expiration",""))[:10]}')
        tw = _sf(position_row.get("transition_target_width"))
        if tw: st.caption(f"Target width: ${tw:.1f}")

    # ── L. Playbook & SOP ────────────────────────────────────────────────────
    pb_code = str(position_row.get("playbook_code","—"))
    pb_name = str(position_row.get("playbook_name","—"))
    pb_status=str(position_row.get("playbook_status","WATCHLIST"))
    STATUS_COLORS={"PROMOTED":"#15803d","WATCHLIST":"#2563eb","LIMITED_USE":"#b45309","DEMOTED":"#dc2626"}
    sc=STATUS_COLORS.get(pb_status,"#6b7280")
    st.divider()
    st.markdown(
        f'<div style="padding:8px 14px;border-radius:8px;border-left:4px solid {sc};background:#0f1117">'
        f'<strong style="color:{sc}">{pb_code}</strong> — {pb_name} &nbsp;|&nbsp; '
        f'<span style="color:{sc}">{pb_status}</span></div>', unsafe_allow_html=True)

    l1,l2,l3=st.columns(3)
    l1.metric("Contract Add",  f'+{int(_sf(position_row.get("transition_final_contract_add",0)))}')
    l2.metric("Capital Decision", str(position_row.get("capital_commitment_decision","NO_ADD")))
    l3.metric("Queue Bias",    f'{_sf(position_row.get("playbook_queue_bias")):+.1f}')

    sop_sections = [
        ("Setup",       position_row.get("sop_setup",[])),
        ("Execution",   position_row.get("sop_execution",[])),
        ("Invalidation",position_row.get("sop_invalidation",[])),
        ("Next Step",   position_row.get("sop_next_step",[])),
    ]
    for label, steps in sop_sections:
        if steps:
            with st.expander(f"SOP: {label}"):
                for s in steps: st.caption(f"• {s}")
    audit_tags = position_row.get("playbook_audit_tags",[])
    if audit_tags: st.caption("Tags: " + " · ".join(audit_tags))

    # ── I. Timing & execution plan ───────────────────────────────────────────
    st.divider()
    st.markdown("**I — Timing & Execution Plan**")
    i1,i2,i3,i4 = st.columns(4)
    i1.metric("Window",    str(position_row.get("transition_time_window","—")))
    i2.metric("Timing Score", f'{_sf(position_row.get("transition_timing_score")):.0f}')
    i3.metric("Policy",    str(position_row.get("transition_execution_policy","DELAY")))
    i4.metric("Schedule",  str(position_row.get("transition_execution_schedule","DEFER")))
    j1,j2,j3 = st.columns(3)
    j1.metric("Now %",  f'{_sf(position_row.get("transition_size_fraction_now"))*100:.0f}%')
    j2.metric("Later %",f'{_sf(position_row.get("transition_size_fraction_later"))*100:.0f}%')
    j3.metric("Next Window", str(position_row.get("transition_next_window","—")))

    # ── J. Vol surface ────────────────────────────────────────────────────────
    st.divider()
    st.markdown("**J — Volatility Surface Quality**")
    k1,k2,k3 = st.columns(3)
    k1.metric("Surface Score",  f'{_sf(position_row.get("transition_execution_surface_score")):.0f}')
    k2.metric("Local Richness", f'{_sf(position_row.get("transition_surface_local_richness")):.3f}')
    k3.metric("Front-Back Edge",f'{_sf(position_row.get("transition_surface_front_back_edge")):.3f}')
    k4,k5 = st.columns(2)
    k4.metric("Long-Short Edge",f'{_sf(position_row.get("transition_surface_long_short_edge")):.3f}')
    k5.metric("Harvest Curve",  f'{_sf(position_row.get("transition_surface_harvest_curve_score")):.0f}')

    # ── K. Analyst view ───────────────────────────────────────────────────────
    st.divider()
    st.markdown("**K — Analyst View**")
    desk=str(position_row.get("transition_desk_note",""))
    if desk: st.info(desk)
    reasons=position_row.get("transition_winner_reasons",[])
    if reasons:
        with st.expander("Why this won"):
            for r in reasons: st.caption(f"✓ {r}")
    rej_sum=str(position_row.get("transition_rejection_summary",""))
    if rej_sum: st.caption(f"**Alternatives:** {rej_sum}")
    inv=position_row.get("transition_invalidation_notes",[])
    if inv:
        with st.expander("Invalidation conditions"):
            for n in inv: st.caption(f"⚠️ {n}")
    nxt=position_row.get("transition_next_roll_notes",[])
    if nxt:
        with st.expander("Next roll plan"):
            for n in nxt: st.caption(f"→ {n}")

    # ── H. Portfolio fit ──────────────────────────────────────────────────────
    alloc = _sf(position_row.get("transition_allocator_score",75.0))
    rec   = _sf(position_row.get("transition_recycling_score"))
    fit   = bool(position_row.get("transition_portfolio_fit_ok",True))
    st.divider()
    st.markdown("**H — Portfolio Fit**")
    h1,h2,h3 = st.columns(3)
    h1.metric("Allocator Score", f"{alloc:.0f}")
    h2.metric("Recycling Score", f"{rec:.0f}")
    h3.metric("Fit OK", "✅" if fit else "❌")

    # Risk notes
    rejected = position_row.get("transition_rejected_candidates") or []
    if rejected:
        with st.expander(f"Rejected candidates ({len(rejected)})"):
            for r in rejected:
                st.caption(f"✗ {r.get('action','?')} — {r.get('reason','')} "
                            f"{'| score '+str(round(r.get('composite_score',r.get('score',0)),1)) if r.get('composite_score') or r.get('score') else ''}")


def render_transition_orders(
    position_row: dict[str, Any],
    ticket:       dict[str, Any],
) -> None:
    """Display the close/open order sequence from a transition ticket."""
    st.markdown("### Execution Sequence")
    st.caption("⚠️ Draft only — review before manual entry in broker.")

    # Net credit
    nc = _sf(ticket.get("estimated_net_credit"))
    col = "#22c55e" if nc >= 1.0 else "#f59e0b" if nc > 0 else "#ef4444"
    st.markdown(
        f'<div style="padding:8px 14px;border-left:4px solid {col};'
        f'background:#0f1117;border-radius:6px;margin-bottom:8px">'
        f'<strong>Estimated conservative net credit: ${nc:.2f}/share</strong></div>',
        unsafe_allow_html=True,
    )

    # Close orders
    close_orders = ticket.get("close_orders", [])
    if close_orders:
        st.markdown("**Step 1 — Close**")
        for o in close_orders:
            st.markdown(
                f'🔴 **{o["action"].replace("_"," ")}** · '
                f'{o.get("description","??")} · '
                f'qty {o.get("quantity",1)} · '
                f'_{o.get("fill_note","")}_'
            )

    # Open orders
    open_orders = ticket.get("open_orders", [])
    if open_orders:
        st.markdown("**Step 2 — Open**")
        for o in open_orders:
            st.markdown(
                f'🟢 **{o["action"].replace("_"," ")}** · '
                f'{o.get("description","??")} · '
                f'qty {o.get("quantity",1)} · '
                f'_{o.get("fill_note","")}_'
            )

    # Post-trade structure
    post = ticket.get("expected_post_structure", {})
    if post:
        st.markdown("**Resulting structure:**")
        st.caption(
            f'{str(post.get("type","")).replace("_"," ").title()} | '
            f'Long: {post.get("long_leg","—")} | '
            f'Short: {post.get("short_leg","—")}'
        )

    # Notes
    notes = ticket.get("notes", [])
    if notes:
        with st.expander("Why this transition was approved"):
            for n in notes:
                st.caption(f"• {n}")
