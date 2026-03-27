"""autopilot/autopilot_renderer.py — Displays the automation boundary map."""
from __future__ import annotations
import streamlit as st
from autopilot.delegation_matrix import DELEGATION_MATRIX

AUTH_COLORS: dict = {"AUTO":"#22c55e","AUTO_DRAFT":"#2563eb","HUMAN_APPROVAL":"#f59e0b",
                      "HUMAN_EXECUTION":"#f97316","NEVER_AUTOMATE":"#ef4444"}

def render_autopilot_boundaries(environment: str="LIVE") -> None:
    st.markdown("### 🛡 Mission Control / Autopilot Boundary")
    st.caption(f"Environment: **{environment}**")
    rules=DELEGATION_MATRIX.get(environment,{})
    import pandas as pd
    rows=[{"Action Family":af,"Authority":auth,
           "Color": AUTH_COLORS.get(auth,"#6b7280")} for af,auth in sorted(rules.items())]
    df=pd.DataFrame(rows)
    st.dataframe(df[["Action Family","Authority"]],use_container_width=True,hide_index=True)
    st.caption("🟢 AUTO  🔵 AUTO_DRAFT  🟡 HUMAN_APPROVAL  🟠 HUMAN_EXECUTION  🔴 NEVER_AUTOMATE")

def render_authority_guard_result(result: dict) -> None:
    if result.get("allowed"):
        st.success(f"✅ Allowed: {result.get('action_family')} at {result.get('requested_authority')}")
    else:
        st.error(f"🚫 Blocked: {result.get('reason','Authority limit exceeded')}")
