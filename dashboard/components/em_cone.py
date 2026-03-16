"""
dashboard/components/em_cone.py
Expected Move Envelope — visual probability bands around spot.

Shows traders at a glance:
  - where price is expected to stay (±1 EM)
  - where credit spread short strikes sit relative to the cone
  - whether debit or credit structures are more appropriate

No new backend dependency — uses spot + expected_move already computed.
"""

import streamlit as st

try:
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False


def build_expected_move_bands(spot: float, expected_move: float) -> dict:
    """
    Compute EM bands centered on spot.
    Returns dict of price levels for chart rendering.
    """
    return {
        "spot":          spot,
        "upper_1em":     round(spot + expected_move, 2),
        "lower_1em":     round(spot - expected_move, 2),
        "upper_0_5em":   round(spot + expected_move * 0.5, 2),
        "lower_0_5em":   round(spot - expected_move * 0.5, 2),
        "upper_1_5em":   round(spot + expected_move * 1.5, 2),
        "lower_1_5em":   round(spot - expected_move * 1.5, 2),
    }


def render_em_cone(
    spot: float,
    expected_move: float,
    top_trade: dict | None = None,
    derived: dict | None = None,
):
    """
    Render the Expected Move Envelope as a horizontal price band chart.

    Overlays:
      - Spot price (center line)
      - ±0.5 EM band (inner — calendar zone)
      - ±1.0 EM band (main — credit spread boundary)
      - ±1.5 EM band (outer — debit spread target)
      - Top trade short/hedge strikes if available
    """
    st.subheader("🎯 Expected Move Envelope")

    bands = build_expected_move_bands(spot, expected_move)

    if not PLOTLY_AVAILABLE:
        # Text fallback
        col1, col2, col3 = st.columns(3)
        col1.metric("Lower EM",  f"${bands['lower_1em']:.2f}")
        col2.metric("Spot",      f"${spot:.2f}")
        col3.metric("Upper EM",  f"${bands['upper_1em']:.2f}")
        return

    fig = go.Figure()

    # ── Band fills ─────────────────────────────────────────────
    # Outer band (±1.5 EM) — debit spread zone
    fig.add_trace(go.Scatter(
        x    = [bands["lower_1_5em"], bands["upper_1_5em"]],
        y    = [0.5, 0.5],
        mode = "lines",
        line = dict(color="rgba(0,0,0,0)"),
        showlegend = False,
        hoverinfo  = "skip",
    ))

    def add_band(low, high, fill_color, name, opacity=0.15):
        fig.add_shape(
            type      = "rect",
            x0        = low,
            x1        = high,
            y0        = 0.15,
            y1        = 0.85,
            fillcolor = fill_color,
            opacity   = opacity,
            line      = dict(width=0),
        )

    # 1.5 EM band — outermost (debit zone)
    add_band(bands["lower_1_5em"], bands["lower_1em"],  "#a855f7", "1.5 EM", 0.12)
    add_band(bands["upper_1em"],   bands["upper_1_5em"], "#a855f7", "1.5 EM", 0.12)

    # 1.0 EM band — credit spread boundary
    add_band(bands["lower_1em"],   bands["lower_0_5em"], "#f59e0b", "1 EM",  0.18)
    add_band(bands["upper_0_5em"], bands["upper_1em"],   "#f59e0b", "1 EM",  0.18)

    # 0.5 EM band — inner calendar zone (green)
    add_band(bands["lower_0_5em"], bands["upper_0_5em"], "#22c55e", "0.5 EM", 0.20)

    # ── Boundary lines ─────────────────────────────────────────
    def vline(x, color, dash, label, y_pos=0.92):
        fig.add_shape(
            type="line", x0=x, x1=x, y0=0.08, y1=0.92,
            line=dict(color=color, width=1.5, dash=dash),
        )
        fig.add_annotation(
            x=x, y=y_pos, yref="paper",
            text=f"${x:.0f}", showarrow=False,
            font=dict(size=10, color=color),
            bgcolor="rgba(15,23,42,0.7)",
            borderpad=2,
        )

    vline(bands["upper_1_5em"], "#7c3aed", "dot",   "1.5 EM")
    vline(bands["upper_1em"],   "#f59e0b", "dash",  "1 EM")
    vline(bands["upper_0_5em"], "#86efac", "dot",   "0.5 EM")
    vline(bands["lower_0_5em"], "#86efac", "dot",   "0.5 EM")
    vline(bands["lower_1em"],   "#f59e0b", "dash",  "1 EM")
    vline(bands["lower_1_5em"], "#7c3aed", "dot",   "1.5 EM")

    # Spot line
    fig.add_shape(
        type="line", x0=spot, x1=spot, y0=0.05, y1=0.95,
        line=dict(color="#ffffff", width=2.5),
    )
    fig.add_annotation(
        x=spot, y=0.5, yref="paper",
        text=f"<b>${spot:.2f}</b>", showarrow=False,
        font=dict(size=12, color="white"),
        bgcolor="rgba(15,23,42,0.85)",
        borderpad=3,
    )

    # ── Overlay top trade strikes ───────────────────────────────
    if top_trade:
        st_type = top_trade.get("strategy_type", "")
        if st_type in ("bear_call", "bull_put"):
            short_s = top_trade.get("short_strike")
            hedge_s = top_trade.get("hedge_strike")
        else:
            short_s = top_trade.get("short_strike")
            hedge_s = top_trade.get("long_strike")

        if short_s:
            fig.add_shape(
                type="line", x0=short_s, x1=short_s, y0=0.1, y1=0.9,
                line=dict(color="#f43f5e", width=2, dash="dash"),
            )
            fig.add_annotation(
                x=short_s, y=0.08, yref="paper",
                text=f"Short<br>${short_s:.0f}",
                showarrow=False, font=dict(size=9, color="#f43f5e"),
                bgcolor="rgba(15,23,42,0.7)", borderpad=2,
            )
        if hedge_s:
            fig.add_shape(
                type="line", x0=hedge_s, x1=hedge_s, y0=0.1, y1=0.9,
                line=dict(color="#94a3b8", width=1.5, dash="dot"),
            )
            fig.add_annotation(
                x=hedge_s, y=0.08, yref="paper",
                text=f"Hedge<br>${hedge_s:.0f}",
                showarrow=False, font=dict(size=9, color="#94a3b8"),
                bgcolor="rgba(15,23,42,0.7)", borderpad=2,
            )

    # ── Zone labels ─────────────────────────────────────────────
    label_y = 0.5
    for x_pos, label, color in [
        (spot,                           "Calendar\nzone",   "#86efac"),
        (bands["upper_1em"] + expected_move * 0.25, "Credit\nzone", "#fcd34d"),
        (bands["upper_1_5em"] + expected_move * 0.15, "Debit\nzone", "#c4b5fd"),
    ]:
        fig.add_annotation(
            x=x_pos, y=label_y, yref="paper",
            text=label, showarrow=False,
            font=dict(size=9, color=color),
            bgcolor="rgba(0,0,0,0)",
        )

    # ── Layout ──────────────────────────────────────────────────
    padding = expected_move * 2.2
    fig.update_layout(
        height        = 160,
        margin        = dict(l=10, r=10, t=10, b=10),
        paper_bgcolor = "rgba(0,0,0,0)",
        plot_bgcolor  = "rgba(0,0,0,0)",
        xaxis = dict(
            range       = [spot - padding, spot + padding],
            showgrid    = False,
            zeroline    = False,
            showticklabels = False,
        ),
        yaxis = dict(
            showgrid       = False,
            zeroline       = False,
            showticklabels = False,
            range          = [0, 1],
        ),
        showlegend = False,
    )

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # Caption legend
    st.caption(
        "🟢 ±0.5 EM — calendar zone &nbsp;|&nbsp; "
        "🟡 ±1.0 EM — credit spread boundary &nbsp;|&nbsp; "
        "🟣 ±1.5 EM — debit spread target &nbsp;|&nbsp; "
        "⬜ spot"
    )
