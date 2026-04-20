"""
dashboard/components/strategy_bars.py
Strategy Strength Bars — shows the engine's strategic mode at a glance.

Answers: "What strategic mode is the engine in right now?"
before the user even looks at individual trade cards.
"""

import streamlit as st

try:
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

STRATEGY_LABELS = {
    "bear_call":       "Bear Call Credit",
    "bull_put":        "Bull Put Credit",
    "bull_call_debit": "Bull Call Debit",
    "bear_put_debit":  "Bear Put Debit",
    "calendar":        "ATM Calendar",
    "bull_diagonal":   "Bull Diagonal",
    "bear_diagonal":   "Bear Diagonal",
}

STRATEGY_COLORS = {
    "bear_call":       "#f97316",   # orange — bearish credit
    "bull_put":        "#22c55e",   # green  — bullish credit
    "bull_call_debit": "#3b82f6",   # blue   — bullish debit
    "bear_put_debit":  "#a855f7",   # purple — bearish debit
    "calendar":        "#06b6d4",   # cyan
    "bull_diagonal":   "#84cc16",   # lime
    "bear_diagonal":   "#ec4899",   # pink
}


def build_strategy_score_dataframe(candidates: list[dict]) -> list[dict]:
    """
    Aggregate candidates into one row per strategy family.
    Uses highest confidence_score within each family.
    Returns list of dicts sorted by score descending.
    """
    best: dict[str, int] = {}
    for c in candidates:
        st_type = c["strategy_type"]
        score   = c["confidence_score"]
        if st_type not in best or score > best[st_type]:
            best[st_type] = score

    rows = []
    for st_type, score in best.items():
        rows.append({
            "strategy_type": st_type,
            "label":         STRATEGY_LABELS.get(st_type, st_type),
            "score":         score,
            "color":         STRATEGY_COLORS.get(st_type, "#6b7280"),
            "strength":      _strength_label(score),
        })

    return sorted(rows, key=lambda r: r["score"], reverse=True)


def _strength_label(score: int) -> str:
    if score >= 80:
        return "Strong"
    elif score >= 65:
        return "Tradable"
    elif score >= 50:
        return "Weak"
    return "Avoid"


def _strength_color(score: int) -> str:
    if score >= 80:
        return "#22c55e"
    elif score >= 65:
        return "#f59e0b"
    elif score >= 50:
        return "#f97316"
    return "#ef4444"


def render_strategy_probability_bars(candidates: list[dict]):
    """
    Render a horizontal bar chart showing strategy strength scores.
    Uses existing candidate data — no new backend dependency.
    """
    st.subheader("📊 Strategy Strength")

    if not candidates:
        st.caption("No candidates — run with live data or mock mode to see strategy scores.")
        return

    rows = build_strategy_score_dataframe(candidates)

    if not PLOTLY_AVAILABLE:
        # Fallback: native Streamlit progress bars
        for row in rows:
            col1, col2, col3 = st.columns([3, 6, 1])
            with col1:
                st.markdown(
                    f'<span style="font-size:13px;font-weight:500">{row["label"]}</span>',
                    unsafe_allow_html=True,
                )
            with col2:
                color = _strength_color(row["score"])
                pct   = row["score"] / 100
                st.markdown(
                    f'<div style="background:#1e293b;border-radius:4px;height:20px;'
                    f'position:relative;overflow:hidden">'
                    f'<div style="width:{pct*100:.0f}%;height:100%;background:{color};'
                    f'border-radius:4px"></div></div>',
                    unsafe_allow_html=True,
                )
            with col3:
                st.markdown(
                    f'<span style="font-size:13px;color:{_strength_color(row["score"])}">'
                    f'{row["score"]}</span>',
                    unsafe_allow_html=True,
                )
        return

    # Plotly horizontal bar chart
    labels  = [r["label"]    for r in rows]
    scores  = [r["score"]    for r in rows]
    colors  = [_strength_color(r["score"]) for r in rows]
    strengths = [r["strength"] for r in rows]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y         = labels,
        x         = scores,
        orientation = "h",
        marker_color = colors,
        text      = [f"{s}  {lbl}" for s, lbl in zip(scores, strengths)],
        textposition = "inside",
        textfont  = dict(size=12, color="white"),
        hovertemplate = "%{y}<br>Score: %{x}/100<extra></extra>",
    ))

    # Reference lines
    for threshold, label, dash in [(80, "Strong", "dot"), (65, "Tradable", "dash")]:
        fig.add_vline(
            x          = threshold,
            line_dash  = dash,
            line_color = "#6b7280",
            line_width = 1,
            annotation_text = label,
            annotation_position = "top",
            annotation_font_size = 10,
            annotation_font_color = "#9ca3af",
        )

    fig.update_layout(
        height          = max(120, len(rows) * 45 + 40),
        margin          = dict(l=0, r=20, t=10, b=10),
        paper_bgcolor   = "rgba(0,0,0,0)",
        plot_bgcolor    = "rgba(0,0,0,0)",
        xaxis = dict(
            range       = [0, 105],
            showgrid    = True,
            gridcolor   = "rgba(255,255,255,0.05)",
            tickfont    = dict(color="#9ca3af", size=11),
            title       = None,
        ),
        yaxis = dict(
            tickfont    = dict(color="#e2e8f0", size=12),
            autorange   = "reversed",
        ),
        showlegend = False,
    )

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
