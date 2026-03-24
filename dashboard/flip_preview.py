"""
dashboard/flip_preview.py
Read-only Preview Flip panel for the Positions tab.

render_flip_preview(position_row) → None

Shows:
  A. Current structure snapshot
  B. Proposed flip target
  C. Market context (skew, sentiment, gamma)
  D. Rationale + risk note

No orders placed. No state mutated.
"""
from __future__ import annotations

from typing import Any

import streamlit as st


# ── Color helpers ─────────────────────────────────────────────────────────────

_FLIP_COLORS = {
    "PIVOT_TO_CALLS":    "#3b82f6",
    "PIVOT_TO_PUTS":     "#ef4444",
    "PIVOT_TO_DIAGONAL": "#7c3aed",
    "HOLD_STRUCTURE":    "#6b7280",
}

_CREDIT_COLOR = lambda c: (
    "#f59e0b" if c >= 5.0 else
    "#22c55e" if c >= 1.0 else
    "#6b7280"
)

_SCORE_LABEL = lambda s: (
    ("STRONG", "#22c55e") if s >= 75 else
    ("MODERATE", "#f59e0b") if s >= 45 else
    ("WEAK", "#6b7280")
)

_sf = lambda v, d=0.0: (float(v) if v not in (None,"","—") else d)


def _badge(text: str, color: str, text_color: str = "#fff") -> str:
    return (f'<span style="background:{color};color:{text_color};'
            f'padding:3px 12px;border-radius:20px;font-size:11px;font-weight:700">{text}</span>')


def render_flip_preview(position_row: dict[str, Any]) -> None:
    """
    Render the full flip preview panel for one position.
    Call inside an st.expander or after a button click.
    """
    flip = position_row.get("flip_summary") or {}
    rec  = str(flip.get("recommendation") or flip.get("flip_type") or
               position_row.get("flip_recommendation","HOLD_STRUCTURE"))
    rec_color   = _FLIP_COLORS.get(rec, "#6b7280")
    flip_credit = _sf(flip.get("flip_roll_credit") or position_row.get("proposed_roll_credit"))
    flip_score  = _sf(flip.get("flip_quality_score") or position_row.get("flip_quality_score"))
    score_label, score_color = _SCORE_LABEL(flip_score)
    rationale   = str(flip.get("rationale") or "No rationale available.")

    # Confidence + risk note
    confidence  = ("HIGH" if flip_score >= 75 else "MEDIUM" if flip_score >= 45 else "LOW")
    risk_note   = _build_risk_note(position_row, flip)

    st.markdown(
        f'<div style="background:#0f1117;border:2px solid {rec_color}44;'
        f'border-radius:12px;padding:16px;margin-bottom:8px">'
        f'<div style="display:flex;justify-content:space-between;align-items:center">'
        f'<span style="font-size:14px;font-weight:700;color:#f9fafb">📊 Flip Preview</span>'
        f'{_badge(rec.replace("_"," "), rec_color)}</div></div>',
        unsafe_allow_html=True,
    )

    # ── A. Current structure ──────────────────────────────────────────────────
    st.markdown("**A — Current Structure**")
    a1,a2,a3,a4,a5 = st.columns(5)
    a1.metric("Symbol",    position_row.get("symbol","—"))
    a2.metric("Strategy",  str(position_row.get("strategy_type","—")).replace("_"," ").title())
    a3.metric("Long $",    f'${_sf(position_row.get("long_strike")):.0f}')
    a4.metric("Short $",   f'${_sf(position_row.get("short_strike")):.0f}')
    a5.metric("Net Liq",   f'${_sf(position_row.get("net_liq")):.0f}')

    # ── B. Proposed flip ─────────────────────────────────────────────────────
    st.divider()
    st.markdown("**B — Proposed Flip**")
    b1,b2,b3,b4 = st.columns(4)
    b1.markdown(f'**Target**<br>{_badge(rec.replace("_"," "), rec_color)}',
                unsafe_allow_html=True)
    target_struct = str(flip.get("flip_target_structure","—")).replace("_"," ").title()
    b2.metric("Target Structure", target_struct)

    credit_col = _CREDIT_COLOR(flip_credit)
    b3.markdown(
        f'**Roll Credit**<br><span style="font-size:20px;font-weight:700;color:{credit_col}">'
        f'${flip_credit:.2f}</span>',
        unsafe_allow_html=True,
    )
    b4.markdown(
        f'**Quality Score**<br>'
        f'<span style="font-size:20px;font-weight:700;color:{score_color}">'
        f'{flip_score:.0f}</span> '
        f'{_badge(score_label, score_color)}',
        unsafe_allow_html=True,
    )

    # ── C. Market context ─────────────────────────────────────────────────────
    st.divider()
    st.markdown("**C — Market Context**")
    c1,c2,c3,c4 = st.columns(4)
    skew_change = _sf(flip.get("skew_change") or position_row.get("current_skew"))
    sentiment   = _sf(position_row.get("sentiment_score"))
    gamma       = str(position_row.get("live_vga","") or "").replace("_"," ").title() or "—"
    trap_dist   = position_row.get("gamma_trap_distance")

    c1.metric("Skew Δ",       f'{skew_change:+.3f}')
    c2.metric("Sentiment",    f'{sentiment:+.2f}')
    c3.metric("VGA Regime",   gamma)
    c4.metric("Trap Distance",
              f'{trap_dist:.1%}' if trap_dist is not None else "—",
              delta="⚠️ Near" if trap_dist is not None and trap_dist < 0.02 else None,
              delta_color="inverse" if trap_dist is not None and trap_dist < 0.02 else "off")

    # ── D. Rationale + risk ───────────────────────────────────────────────────
    st.divider()
    st.markdown("**D — Decision Basis**")
    st.info(f"**Why this flip:** {rationale}")
    if risk_note:
        st.warning(f"**Risk note:** {risk_note}")
    st.caption(f"Confidence: **{confidence}**  |  Score threshold: 20+ to qualify")

    # All flip optimizer candidates (expandable)
    all_cands = flip.get("all_candidates")
    if all_cands:
        with st.expander("All flip candidates scored"):
            for cand in all_cands:
                col = _FLIP_COLORS.get(cand.get("flip_type",""), "#6b7280")
                valid_str = "✓ VALID" if cand.get("valid") else "✗ BLOCKED"
                st.markdown(
                    f'{_badge(cand.get("flip_type","?").replace("_"," "), col)} '
                    f'score={cand.get("flip_quality_score",0):.0f} '
                    f'credit=${_sf(cand.get("flip_roll_credit")):.2f} '
                    f'— {valid_str} — {cand.get("rationale","")}',
                    unsafe_allow_html=True,
                )

    # ── Live selector candidates ──────────────────────────────────────────────
    roll_preview = position_row.get("roll_preview") or {}
    sel_cands    = position_row.get("roll_candidate_inputs") or []

    if roll_preview and isinstance(roll_preview, dict):
        best_roll = roll_preview.get("best_roll")
        if best_roll:
            st.divider()
            st.markdown("**E — Best Live Roll Candidate**")
            action_col = {"GOLD HARVEST":"#f59e0b","ROLL":"#22c55e","WATCH":"#3b82f6"}.get(
                best_roll.get("action_label",""), "#6b7280")
            e1, e2, e3, e4 = st.columns(4)
            e1.markdown(
                f'<span style="background:{action_col};color:#fff;padding:3px 12px;'
                f'border-radius:20px;font-size:11px;font-weight:700">'
                f'{best_roll.get("action_label","—")}</span>',
                unsafe_allow_html=True,
            )
            e2.metric("Roll Credit",  f'${_sf(best_roll.get("estimated_roll_credit")):.2f}')
            e3.metric("Max Loss",     f'${_sf(best_roll.get("estimated_max_loss")):.0f}')
            e4.metric("Score",        f'{_sf(best_roll.get("quality_score")):.0f}')

            st.caption(
                f'**{best_roll.get("target_structure","").replace("_"," ").title()}** '
                f'${best_roll.get("target_short_strike",0):.0f}/'
                f'${best_roll.get("target_long_strike",0):.0f} | '
                f'{best_roll.get("target_short_expiration","—")} / '
                f'{best_roll.get("target_long_expiration","—")}'
            )
            st.caption(best_roll.get("rationale",""))

    if len(sel_cands) > 1:
        with st.expander(f"All {len(sel_cands)} live structure candidates"):
            import pandas as pd
            rows = []
            for sc in sel_cands[:10]:
                rows.append({
                    "Structure": sc.get("target_structure","").replace("_"," ").title(),
                    "Short $":   sc.get("target_short_strike",""),
                    "Long $":    sc.get("target_long_strike",""),
                    "Exp":       sc.get("target_short_expiration",""),
                    "Credit":    f'${_sf(sc.get("estimated_opening_credit_or_debit")):.2f}',
                    "Score":     f'{_sf(sc.get("selector_score")):.0f}',
                    "Rolls→Free": sc.get("rolls_to_free_heuristic","—"),
                    "Gold ETA":  sc.get("gold_harvest_eta_heuristic","—"),
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _build_risk_note(position_row: dict, flip: dict) -> str:
    """Generate a concise risk note based on the flip type and position state."""
    rec          = str(flip.get("recommendation","HOLD_STRUCTURE"))
    flip_credit  = _sf(flip.get("flip_roll_credit") or position_row.get("proposed_roll_credit"))
    assignment   = bool((position_row.get("harvest_summary") or {}).get("assignment_risk"))
    trap_dist    = position_row.get("gamma_trap_distance")

    if assignment:
        return "Assignment risk present — confirm short leg position before flipping."
    if trap_dist is not None and trap_dist < 0.02:
        return "Spot is near gamma trap — flip may not improve stability."
    if rec == "PIVOT_TO_CALLS" and flip_credit < 3.0:
        return "Credit is below preferred threshold. Flip improves structure but extraction is limited."
    if rec == "PIVOT_TO_PUTS":
        return "Flipping to puts increases directional risk in bearish gamma environment."
    if rec == "PIVOT_TO_DIAGONAL":
        return "Converting to diagonal maintains long anchor but adds directional short exposure."
    return ""
