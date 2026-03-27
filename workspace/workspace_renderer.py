"""workspace/workspace_renderer.py — Renders the guided workspace in the cockpit."""
from __future__ import annotations
import streamlit as st

READINESS_COLORS={"READY":"#22c55e","READY_WITH_CAUTION":"#f59e0b","REVIEW_REQUIRED":"#f59e0b","BLOCKED":"#ef4444"}

def render_workspace(workspace: dict) -> None:
    st.markdown("### 🖥 Operator Execution Workspace")
    selected=workspace.get("selected_path",{}); alt=workspace.get("alternative_path"); readiness=workspace.get("ticket_readiness",{})
    c1,c2=st.columns(2)
    c1.metric("Symbol",workspace.get("symbol","?"))
    c1.metric("Selected Path",selected.get("path_code","N/A"))
    if alt: c2.metric("Alternative",alt.get("path_code","N/A"))
    c2.metric("Path Score",f'{selected.get("path_total_score",0):.1f}')

    if workspace.get("primary_rationale"):
        with st.expander("Rationale"): st.write(workspace["primary_rationale"])

    steps=workspace.get("sop_steps",[])
    if steps:
        with st.expander(f"SOP Steps ({len(steps)})"):
            for s in steps: st.caption(f"{s['step']}. {s['label']}")

    blockers=workspace.get("blockers",[])
    if blockers:
        st.markdown("**Blockers**")
        for b in blockers: st.error(f"[{b['type']}] {b['summary']}")

    status=readiness.get("status","?"); color=READINESS_COLORS.get(status,"#6b7280")
    st.markdown(f'<div style="padding:6px 12px;border-left:4px solid {color};background:#0f1117;border-radius:6px">'
                f'<strong style="color:{color}">Ticket Readiness: {status}</strong> — {readiness.get("summary","")}'
                f'</div>', unsafe_allow_html=True)

    tasks=workspace.get("post_action_tasks",[])
    if tasks:
        with st.expander("Post-Action Tasks"):
            for t in tasks: st.caption(f"• {t['task']}: {t['summary']}")

    kc=workspace.get("knowledge_context_summaries",[])
    if kc:
        with st.expander(f"Knowledge Context ({len(kc)})"):
            for note in kc: st.caption(f"📌 {note}")
