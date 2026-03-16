"""
dashboard/components/gamma_wall.py
Gamma / OI Wall Chart — shows gamma support and resistance zones.

Phase 1 (now):  OI proxy — aggregates open interest by strike.
                Works with any chain data. No GEX engine required.
                Labeled "OI Wall / Gamma Proxy" to be transparent.

Phase 2 (later): Replace with true signed GEX once gamma_engine.py
                 aggregation is wired into the live data pipeline.
                 Just swap build_gamma_wall_dataframe() — chart unchanged.

Why this matters:
  - Large OI concentrations act as magnet/resistance levels
  - Helps identify where market makers are positioned
  - Confirms or challenges expected move boundaries
"""

import streamlit as st

try:
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False


def build_gamma_wall_dataframe(chain: list[dict], spot: float) -> list[dict]:
    """
    Aggregate chain data into per-strike gamma/OI summary.

    Phase 1: Uses open_interest as proxy for gamma concentration.
             Signs it: calls = positive, puts = negative.
    Phase 2: Replace with true GEX = gamma * OI * 100 * spot.

    Returns list of dicts sorted by strike, filtered to ±15% of spot.
    """
    strike_map: dict[float, dict] = {}

    for row in chain:
        k  = row["strike"]
        oi = row.get("open_interest", 0) or 0

        # Filter to relevant strikes only (±15% of spot)
        if abs(k - spot) / spot > 0.15:
            continue

        if k not in strike_map:
            strike_map[k] = {"call_oi": 0, "put_oi": 0, "call_gex": 0.0, "put_gex": 0.0}

        gamma = row.get("gamma") or 0.0

        if row["option_type"] == "call":
            strike_map[k]["call_oi"]  += oi
            # True GEX when gamma available, else OI proxy
            if gamma:
                strike_map[k]["call_gex"] += gamma * oi * 100 * spot
            else:
                strike_map[k]["call_gex"] += oi   # OI proxy
        else:
            strike_map[k]["put_oi"]  += oi
            if gamma:
                strike_map[k]["put_gex"] -= gamma * oi * 100 * spot
            else:
                strike_map[k]["put_gex"] -= oi    # OI proxy (negative)

    rows = []
    for k, v in sorted(strike_map.items()):
        net_gex   = v["call_gex"] + v["put_gex"]
        total_oi  = v["call_oi"]  + v["put_oi"]
        has_gamma = any(
            r.get("gamma") for r in chain
            if r["strike"] == k and abs(r.get("gamma") or 0) > 0
        )
        rows.append({
            "strike":    k,
            "net_gex":   round(net_gex, 2),
            "call_oi":   v["call_oi"],
            "put_oi":    v["put_oi"],
            "total_oi":  total_oi,
            "has_gamma": has_gamma,
        })

    return rows


def render_gamma_wall(
    chain: list[dict],
    spot: float,
    gamma_flip: float | None = None,
    top_n_strikes: int = 20,
):
    """
    Render the Gamma Wall / OI Wall chart.

    Shows net gamma exposure (or OI proxy) by strike as horizontal bars.
    Green = positive gamma (call-dominant = pinning force)
    Red   = negative gamma (put-dominant = potential acceleration)
    """
    st.subheader("🧱 Gamma Structure")

    if not chain:
        st.caption("No chain data available.")
        return

    rows = build_gamma_wall_dataframe(chain, spot)

    if not rows:
        st.caption("No strikes within ±15% of spot found in chain.")
        return

    # Detect if we have real gamma or just OI proxy
    has_real_gamma = any(r["has_gamma"] for r in rows)
    chart_label    = "Net GEX" if has_real_gamma else "OI Wall (Gamma Proxy)"

    # Take top N by absolute value centered around spot
    rows_sorted = sorted(rows, key=lambda r: abs(r["strike"] - spot))[:top_n_strikes]
    rows_sorted = sorted(rows_sorted, key=lambda r: r["strike"])

    if not PLOTLY_AVAILABLE:
        st.caption(f"{chart_label} — install plotly for chart view")
        for r in rows_sorted[-8:]:
            marker = "▲" if r["net_gex"] > 0 else "▼"
            color  = "🟢" if r["net_gex"] > 0 else "🔴"
            spot_marker = " ← spot" if abs(r["strike"] - spot) < 2.5 else ""
            st.caption(f"{color} ${r['strike']:.0f}{spot_marker}  {marker} {r['total_oi']:,} OI")
        return

    strikes  = [r["strike"]  for r in rows_sorted]
    net_gex  = [r["net_gex"] for r in rows_sorted]
    total_oi = [r["total_oi"] for r in rows_sorted]

    bar_colors = ["#22c55e" if v >= 0 else "#ef4444" for v in net_gex]

    hover_text = [
        f"Strike: ${s:.0f}<br>"
        f"{'Net GEX' if has_real_gamma else 'Net OI'}: {g:,.0f}<br>"
        f"Total OI: {oi:,}"
        for s, g, oi in zip(strikes, net_gex, total_oi)
    ]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y            = [f"${s:.0f}" for s in strikes],
        x            = net_gex,
        orientation  = "h",
        marker_color = bar_colors,
        marker_opacity = 0.85,
        hovertext    = hover_text,
        hoverinfo    = "text",
        name         = chart_label,
    ))

    # Spot line
    fig.add_vline(
        x=0, line_color="rgba(255,255,255,0.15)", line_width=1,
    )

    # Spot strike marker
    closest_idx = min(range(len(strikes)), key=lambda i: abs(strikes[i] - spot))
    fig.add_annotation(
        y    = f"${strikes[closest_idx]:.0f}",
        x    = 0,
        text = f"  ◄ Spot ${spot:.2f}",
        showarrow = False,
        font = dict(size=10, color="#94a3b8"),
        xanchor = "left",
    )

    # Gamma flip line if available
    if gamma_flip:
        fig.add_hline(
            y         = f"${gamma_flip:.0f}",
            line_dash = "dash",
            line_color = "#f59e0b",
            line_width = 1.5,
            annotation_text = f"Gamma Flip ${gamma_flip:.0f}",
            annotation_position = "right",
            annotation_font_color = "#f59e0b",
            annotation_font_size  = 10,
        )

    fig.update_layout(
        height        = max(250, len(rows_sorted) * 22 + 40),
        margin        = dict(l=10, r=10, t=10, b=10),
        paper_bgcolor = "rgba(0,0,0,0)",
        plot_bgcolor  = "rgba(0,0,0,0)",
        xaxis = dict(
            showgrid    = True,
            gridcolor   = "rgba(255,255,255,0.05)",
            zeroline    = True,
            zerolinecolor = "rgba(255,255,255,0.2)",
            tickfont    = dict(color="#9ca3af", size=10),
            title       = dict(text=chart_label, font=dict(color="#6b7280", size=11)),
        ),
        yaxis = dict(
            tickfont    = dict(color="#e2e8f0", size=11),
            autorange   = "reversed",
            tickmode    = "array",
            tickvals    = [f"${s:.0f}" for s in strikes],
        ),
        showlegend = False,
    )

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # Label transparency
    proxy_note = "" if has_real_gamma else " &nbsp;|&nbsp; 📊 Using OI proxy (real GEX in Phase 2)"
    st.caption(
        f"🟢 Positive = call-dominant (pinning) &nbsp;|&nbsp; "
        f"🔴 Negative = put-dominant (acceleration risk)"
        f"{proxy_note}"
    )
