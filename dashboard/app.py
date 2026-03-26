"""
dashboard/app.py
Options AI Assistant — Streamlit Dashboard

Run locally:
    streamlit run dashboard/app.py

Deploy:
    Push repo to GitHub → connect at share.streamlit.io
    Add MASSIVE_API_KEY (and optionally TRADIER_TOKEN) as secrets

DATA_MODE is controlled by the sidebar dropdown.
"""

import sys
import os
from pathlib import Path

# ── Path setup — works locally and on Streamlit Cloud ────────────────────────
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st
try:
    import plotly
except ImportError:
    pass

# ── Page config — must be first Streamlit call ────────────────────────────────
st.set_page_config(
    page_title="Options AI Assistant",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Operator console link in sidebar
with st.sidebar:
    st.caption("⚙️ [Operator Console](operator_dashboard_app.py)")
    st.divider()

# ── Imports after path setup ──────────────────────────────────────────────────
from data.mock_data import load_mock_market, build_mock_chain
from engines.expected_move  import compute_expected_move
from engines.atr_engine     import classify_atr_trend, em_atr_ratio
from engines.iv_regime      import classify_iv_regime
from engines.term_structure import compute_term_slope, classify_term_structure
from engines.skew_engine    import compute_skew, classify_skew
from engines.context_builder import build_derived
from strategies.bear_call       import generate_bear_call_spreads
from strategies.bull_put        import generate_bull_put_spreads
from strategies.bull_call_debit import generate_bull_call_debit_spreads
from strategies.bear_put_debit  import generate_bear_put_debit_spreads
from strategies.calendar        import generate_calendar_candidates
from strategies.diagonal        import generate_diagonal_candidates
from calculator.trade_scoring   import rank_candidates, get_score_breakdown
from config.settings            import SCORE_STRONG, SCORE_TRADABLE
from backtest.trade_logger      import TradeLogger
from position_manager.position_tracker import PositionTracker
from dashboard.components.strategy_bars import render_strategy_probability_bars
from dashboard.components.em_cone       import render_em_cone
from dashboard.components.gamma_wall    import render_gamma_wall


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

STRATEGY_LABELS = {
    "bear_call":       "Bear Call Credit Spread",
    "bull_put":        "Bull Put Credit Spread",
    "bull_call_debit": "Bull Call Debit Spread",
    "bear_put_debit":  "Bear Put Debit Spread",
}

def score_color(score: int) -> str:
    if score >= SCORE_STRONG:
        return "#22c55e"    # green
    elif score >= SCORE_TRADABLE:
        return "#f59e0b"    # amber
    return "#ef4444"        # red

def score_label(score: int) -> str:
    if score >= SCORE_STRONG:
        return "★ STRONG"
    elif score >= SCORE_TRADABLE:
        return "○ TRADABLE"
    return "✗ SKIP"

def regime_color(regime: str) -> str:
    colors = {
        "cheap":                   "#22c55e",
        "moderate":                "#f59e0b",
        "elevated":                "#f97316",
        "rich":                    "#ef4444",
        "contango":                "#22c55e",
        "flat":                    "#f59e0b",
        "backwardation":           "#ef4444",
        "positive":                "#22c55e",
        "neutral":                 "#f59e0b",
        "negative":                "#ef4444",
        "unknown":                 "#6b7280",
        "high_put_skew":           "#f97316",
        "normal_skew":             "#22c55e",
        "flat_skew":               "#f59e0b",
        "rising":                  "#ef4444",
        "falling":                 "#22c55e",
        # VGA environments
        "premium_selling":         "#22c55e",
        "neutral_time_spreads":    "#3b82f6",
        "cautious_directional":    "#f59e0b",
        "trend_directional":       "#f97316",
        "mixed":                   "#6b7280",
    }
    return colors.get(regime, "#6b7280")

def colored_badge(label: str, color: str) -> str:
    return (
        f'<span style="background:{color}20;color:{color};'
        f'padding:2px 10px;border-radius:12px;font-size:13px;'
        f'font-weight:600;border:1px solid {color}40">{label}</span>'
    )


# ─────────────────────────────────────────────
# DERIVED BUILDER
# ─────────────────────────────────────────────




# ─────────────────────────────────────────────
# DATA LOADER
# ─────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)   # cache 5 min
def load_data(symbol: str, data_mode: str) -> tuple[dict, list[dict]]:
    """Load market + chain. Cached for 5 minutes to avoid hammering API."""
    if data_mode == "mock":
        return load_mock_market(), build_mock_chain()

    elif data_mode == "massive":
        from data_sources.massive_api import (
            get_spot_price, get_expirations, get_option_chain,
            pick_short_expiration, pick_long_expiration,
            extract_atm_straddle, extract_front_iv, extract_skew_25d,
            _compute_dte,
        )
        spot        = get_spot_price(symbol)
        expirations = get_expirations(symbol)
        short_exp   = pick_short_expiration(expirations)
        long_exp    = pick_long_expiration(expirations)
        short_chain = get_option_chain(symbol, short_exp)
        long_chain  = get_option_chain(symbol, long_exp)
        chain       = short_chain + long_chain

        market = load_mock_market()
        market["symbol"]           = symbol.upper()
        market["spot_price"]       = spot
        market["front_dte"]        = _compute_dte(short_exp)
        market["short_dte_target"] = _compute_dte(short_exp)
        market["long_dte_target"]  = _compute_dte(long_exp)

        straddle = extract_atm_straddle(short_chain, spot, _compute_dte(short_exp))
        market["atm_call_mid"] = straddle["atm_call_mid"]
        market["atm_put_mid"]  = straddle["atm_put_mid"]

        front_iv = extract_front_iv(short_chain, _compute_dte(short_exp))
        back_iv  = extract_front_iv(long_chain,  _compute_dte(long_exp))
        if front_iv: market["front_iv"] = front_iv; market["iv_percentile"] = 50.0
        if back_iv:  market["back_iv"]  = back_iv

        skew = extract_skew_25d(short_chain, _compute_dte(short_exp))
        market["put_25d_iv"]        = skew.get("put_25d_iv")
        market["call_25d_iv"]       = skew.get("call_25d_iv")
        market["total_gex"]         = None
        market["gamma_flip"]        = None
        market["gamma_trap_strike"] = None
        return market, chain

    elif data_mode == "tradier":
        from data_sources.tradier_api import (
            get_spot_price, get_expirations, get_option_chain,
            pick_short_expiration, pick_long_expiration,
            extract_atm_straddle, extract_front_iv, extract_skew_25d,
            _compute_dte,
        )
        spot        = get_spot_price(symbol)
        expirations = get_expirations(symbol)
        short_exp   = pick_short_expiration(expirations)
        long_exp    = pick_long_expiration(expirations)
        short_chain = get_option_chain(symbol, short_exp)
        long_chain  = get_option_chain(symbol, long_exp)
        chain       = short_chain + long_chain

        market = load_mock_market()
        market["symbol"]           = symbol.upper()
        market["spot_price"]       = spot
        market["front_dte"]        = _compute_dte(short_exp)
        market["short_dte_target"] = _compute_dte(short_exp)
        market["long_dte_target"]  = _compute_dte(long_exp)

        straddle = extract_atm_straddle(short_chain, spot, _compute_dte(short_exp))
        market["atm_call_mid"] = straddle["atm_call_mid"]
        market["atm_put_mid"]  = straddle["atm_put_mid"]

        front_iv = extract_front_iv(short_chain, _compute_dte(short_exp))
        back_iv  = extract_front_iv(long_chain,  _compute_dte(long_exp))
        if front_iv: market["front_iv"] = front_iv; market["iv_percentile"] = 50.0
        if back_iv:  market["back_iv"]  = back_iv

        skew = extract_skew_25d(short_chain, _compute_dte(short_exp))
        market["put_25d_iv"]        = skew.get("put_25d_iv")
        market["call_25d_iv"]       = skew.get("call_25d_iv")
        market["total_gex"]         = None
        market["gamma_flip"]        = None
        market["gamma_trap_strike"] = None
        return market, chain

    raise ValueError(f"Unknown data_mode: {data_mode!r}")


def generate_candidates(market, chain, derived):
    candidates = []
    candidates += generate_bear_call_spreads(market, chain, derived)
    candidates += generate_bull_put_spreads(market, chain, derived)
    candidates += generate_bull_call_debit_spreads(market, chain, derived)
    candidates += generate_bear_put_debit_spreads(market, chain, derived)
    candidates += generate_calendar_candidates(market, chain, derived)
    candidates += generate_diagonal_candidates(market, chain, derived)
    return rank_candidates(candidates)


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────

def render_sidebar() -> tuple[str, str]:
    with st.sidebar:
        st.title("⚙️ Settings")
        st.divider()

        symbol = st.text_input(
            "Underlying",
            value=st.session_state.get("sidebar_symbol", "SPY"),
            placeholder="e.g. TSLA, SPY, QQQ",
            help="Type any ticker — supports all symbols available from your data source.",
        ).upper().strip() or "SPY"
        st.session_state["sidebar_symbol"] = symbol
        # Quick-pick buttons
        _qp_cols = st.columns(6)
        for _i, _sym in enumerate(["SPY","QQQ","TSLA","AAPL","MSFT","IWM"]):
            if _qp_cols[_i].button(_sym, key=f"qp_{_sym}", use_container_width=True):
                st.session_state["sidebar_symbol"] = _sym
                st.rerun()

        data_mode = st.selectbox(
            "Data Source",
            ["mock", "massive", "tradier"],
            index=0,
            help="mock = static test data | massive = Polygon/Massive API | tradier = Tradier brokerage API",
        )

        st.divider()
        st.markdown("**Risk Settings**")
        risk_dollars = st.slider(
            "Max Risk per Trade ($)",
            min_value=100,
            max_value=5000,
            value=500,
            step=100,
        )

        st.divider()
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        st.divider()
        st.markdown(
            '<p style="font-size:11px;color:#6b7280">Data cached 5 min.<br>'
            'Greeks delayed 15 min on Starter plan.<br>'
            'Not financial advice.</p>',
            unsafe_allow_html=True,
        )

    return symbol, data_mode, risk_dollars


# ─────────────────────────────────────────────
# MARKET SUMMARY PANEL
# ─────────────────────────────────────────────

def _render_vga_decision_box(derived: dict, market: dict) -> None:
    """
    VGA Decision Box — replaces a plain badge with an actionable panel.
    Answers: 'What type of trade should I place right now?'
    """
    vga = derived.get("vga_environment", "mixed")

    _meta = {
        "premium_selling": (
            "🟢", "PREMIUM SELLING", "Credit spreads preferred",
            ["Bull Put Credit", "Bear Call Credit", "Iron Condor"],
            ["Wide debit spreads", "Aggressive directional bets"],
        ),
        "neutral_time_spreads": (
            "🔵", "NEUTRAL TIME SPREADS", "Calendars preferred",
            ["ATM Calendars", "Diagonals"],
            ["Wide credit spreads", "Trend chasing"],
        ),
        "cautious_directional": (
            "🟡", "CAUTIOUS DIRECTIONAL", "Small directional trades only",
            ["Small debit spreads", "Tight diagonals"],
            ["Large position size", "ATM calendars"],
        ),
        "trend_directional": (
            "🟠", "TREND DIRECTIONAL", "Directional trades",
            ["Bull/Bear debit spreads", "Diagonals"],
            ["Credit spreads", "Calendars"],
        ),
        "mixed": (
            "⚫", "MIXED / UNCLEAR", "Reduce size or wait",
            ["Small defined-risk only"],
            ["Full-size trades", "New calendars"],
        ),
    }

    icon, label, guidance, primary, avoid = _meta.get(
        vga, ("⚫", "UNKNOWN", "No guidance", [], [])
    )
    color = regime_color(vga)

    # Confidence from alignment of IV + gamma
    iv_r  = derived.get("iv_regime", "")
    gma_r = derived.get("gamma_regime", "")
    if vga == "premium_selling" and iv_r in ("elevated", "rich") and gma_r == "positive":
        confidence, conf_color = "HIGH — IV + Gamma fully aligned", "#22c55e"
    elif vga == "mixed" or "unknown" in (iv_r, gma_r):
        confidence, conf_color = "LOW — incomplete data",            "#6b7280"
    else:
        confidence, conf_color = "MEDIUM — borderline regime",        "#f59e0b"

    primary_html = "".join(
        f'<div style="font-size:12px;color:#e5e7eb;margin:1px 0">✓ {s}</div>'
        for s in primary
    )
    avoid_html = "".join(
        f'<div style="font-size:12px;color:#9ca3af;margin:1px 0">✗ {s}</div>'
        for s in avoid
    )

    st.markdown(
        f'<div style="background:{color}12;border:1px solid {color}40;'
        f'border-radius:12px;padding:16px 20px;margin-bottom:12px">'
        f'<div style="font-size:10px;color:#9ca3af;text-transform:uppercase;'
        f'letter-spacing:1px;margin-bottom:4px">Market Mode</div>'
        f'<div style="font-size:22px;font-weight:800;color:{color};margin-bottom:2px">'
        f'{icon} {label}</div>'
        f'<div style="font-size:13px;color:#d1d5db;margin-bottom:12px">{guidance}</div>'
        f'<div style="display:flex;gap:32px">'
        f'<div><div style="font-size:10px;color:#6b7280;text-transform:uppercase;'
        f'margin-bottom:4px">🎯 Primary</div>{primary_html}</div>'
        f'<div><div style="font-size:10px;color:#6b7280;text-transform:uppercase;'
        f'margin-bottom:4px">⚠️ Avoid</div>{avoid_html}</div>'
        f'<div><div style="font-size:10px;color:#6b7280;text-transform:uppercase;'
        f'margin-bottom:4px">📊 Confidence</div>'
        f'<div style="font-size:12px;color:{conf_color};font-weight:600">'
        f'{confidence}</div></div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )


def render_market_summary(market: dict, derived: dict):
    st.subheader(f"📈 {market['symbol']} Market Overview")

    spot  = market["spot_price"]
    em    = derived["expected_move"]
    ratio = derived["em_atr_ratio"]

    # Top metric row
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Spot Price",      f"${spot:.2f}")
    c2.metric("Expected Move",   f"±${em:.2f}")
    c3.metric("Upper EM",        f"${derived['upper_em']:.2f}")
    c4.metric("Lower EM",        f"${derived['lower_em']:.2f}")
    c5.metric("EM/ATR Ratio",    f"{ratio:.2f}",
              delta="Range-bound" if ratio > 3 else "Breakout risk" if ratio < 2 else "Balanced",
              delta_color="normal" if ratio > 3 else "inverse")

    st.divider()

    # ── VGA Decision Box ──────────────────────────────────────────────────────
    _render_vga_decision_box(derived, market)

    # Regime badges row — 7 columns
    col1, col2, col3, col4, col5, col6, col7 = st.columns(7)

    with col1:
        st.markdown("**IV Regime**")
        r = derived["iv_regime"]
        st.markdown(colored_badge(r.upper(), regime_color(r)), unsafe_allow_html=True)
        st.caption(f"IV%ile: {market.get('iv_percentile', 50):.0f}")

    with col2:
        st.markdown("**Term Structure**")
        r = derived["term_structure"]
        st.markdown(colored_badge(r.upper(), regime_color(r)), unsafe_allow_html=True)
        st.caption(f"Slope: {derived['term_slope']:.1f}")

    with col3:
        st.markdown("**Skew**")
        r = derived["skew_state"]
        sv = derived.get("skew_value")
        st.markdown(colored_badge(r.replace("_", " ").upper(), regime_color(r)), unsafe_allow_html=True)
        st.caption(f"25Δ skew: {sv:.1f}" if sv else "25Δ skew: N/A")

    with col4:
        st.markdown("**ATR Trend**")
        r = derived["atr_trend"]
        st.markdown(colored_badge(r.upper(), regime_color(r)), unsafe_allow_html=True)
        st.caption(f"ATR(14): ${market.get('atr_14', 0):.2f}")

    with col5:
        st.markdown("**Gamma Regime**")
        r = derived["gamma_regime"]
        st.markdown(colored_badge(r.upper(), regime_color(r)), unsafe_allow_html=True)
        gf = derived.get("gamma_flip")
        st.caption(f"Flip: ${gf:.0f}" if gf else "Flip: N/A")

    with col6:
        st.markdown("**Gamma Trap**")
        gt   = derived.get("gamma_trap")
        spot = market["spot_price"]
        if gt:
            trap_dist  = round(gt - spot, 1)
            trap_color = "#22c55e" if abs(trap_dist) <= derived.get("expected_move", 9) * 0.5 else "#f59e0b"
            st.markdown(colored_badge(f"${gt:.0f}", trap_color), unsafe_allow_html=True)
            st.caption(f"Distance: {trap_dist:+.1f} pts")
        else:
            st.markdown(colored_badge("N/A", "#6b7280"), unsafe_allow_html=True)
            st.caption("No gamma trap")

    with col7:
        vga       = derived.get("vga_environment", "mixed")
        _vga_short = {
            "premium_selling":      "PREMIUM",
            "neutral_time_spreads": "TIME SPREAD",
            "cautious_directional": "CAUTIOUS",
            "trend_directional":    "TREND",
            "mixed":                "MIXED",
        }
        vga_color = regime_color(vga)
        st.markdown("**VGA**")
        st.markdown(colored_badge(_vga_short.get(vga, "?"), vga_color), unsafe_allow_html=True)
        st.caption(derived.get("vga_environment", "mixed").replace("_", " "))


# ─────────────────────────────────────────────
# TRADE CARD
# ─────────────────────────────────────────────

def render_trade_card(rank: int, t: dict, derived: dict):
    label  = STRATEGY_LABELS.get(t["strategy_type"], t["strategy_type"])
    score  = t["confidence_score"]
    credit = t["entry_debit_credit"]
    color  = score_color(score)
    sl     = score_label(score)

    with st.container():
        # Header
        hc1, hc2 = st.columns([3, 1])
        with hc1:
            st.markdown(
                f"### #{rank} &nbsp; {label}",
                unsafe_allow_html=True,
            )
            dir_color = "#22c55e" if t["direction"] == "bullish" else "#ef4444"
            st.markdown(
                colored_badge(t["direction"].upper(), dir_color),
                unsafe_allow_html=True,
            )
        with hc2:
            st.markdown(
                f'<div style="text-align:right">'
                f'<span style="font-size:28px;font-weight:700;color:{color}">'
                f'{score}</span>'
                f'<span style="font-size:13px;color:{color}"> /100</span><br>'
                f'<span style="color:{color};font-size:13px">{sl}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

        st.markdown("")

        # Strike details
        mc1, mc2, mc3, mc4 = st.columns(4)

        # Expiration display — single for verticals, dual for calendars/diagonals
        is_time_spread = t["strategy_type"] in ("calendar", "diagonal")
        short_dte_val  = t.get("short_dte", "")
        long_dte_val   = t.get("long_dte", "")

        if is_time_spread:
            exp_display  = f"{t['short_expiration']} ({short_dte_val}d)"
            lexp_display = f"{t['long_expiration']} ({long_dte_val}d)"
        else:
            exp_display = f"{t['short_expiration']} ({short_dte_val}d)" if short_dte_val else t["short_expiration"]

        if t["strategy_type"] in ("bear_call", "bull_put"):
            mc1.metric("Short Strike", f"${t['short_strike']:.0f}",
                       delta=f"Δ {t['short_delta']:.2f}")
            mc2.metric("Long Strike",  f"${t['hedge_strike']:.0f}",
                       delta=f"Δ {t['hedge_delta']:.2f}")
            mc3.metric("Credit",       f"${credit:.2f}",
                       delta=f"${credit*100:.0f}/contract")
            mc4.metric("Expiration",   exp_display)
        elif t["strategy_type"] in ("calendar", "diagonal"):
            mc1.metric("Long Strike",  f"${t['long_strike']:.0f}",
                       delta=f"Δ {t.get('long_delta', 0):.2f}")
            mc2.metric("Short Strike", f"${t['short_strike']:.0f}",
                       delta=f"Δ {t.get('short_delta', 0):.2f}")
            mc3.metric("Short Exp",    exp_display)
            mc4.metric("Long Exp",     lexp_display)
        else:
            mc1.metric("Long Strike",  f"${t['long_strike']:.0f}",
                       delta=f"Δ {t['long_delta']:.2f}")
            mc2.metric("Short Strike", f"${t['short_strike']:.0f}",
                       delta=f"Δ {t['short_delta']:.2f}")
            mc3.metric("Debit",        f"${abs(credit):.2f}",
                       delta=f"${abs(credit)*100:.0f}/contract")
            mc4.metric("Expiration",   exp_display)

        # Risk row
        rc1, rc2, rc3, rc4, rc5 = st.columns(5)
        mp_str = f"${t['max_profit']:.0f}" if t.get('max_profit') is not None else "Open"
        rc1.metric("Max Profit",   mp_str)
        rc2.metric("Max Loss",     f"${t['max_loss']:.0f}")
        rc3.metric("Target Exit",  f"${t['target_exit_value']:.2f}")
        rc4.metric("Stop Level",   f"${t['stop_value']:.2f}")
        rc5.metric("Contracts",    str(t["contracts"]),
                   delta=f"${t['max_loss'] * t['contracts']:.0f} total risk",
                   delta_color="inverse")

        # Probability row
        p1, p2, p3 = st.columns([1, 1, 4])
        p1.metric("Prob ITM",   f"{t['prob_itm_proxy']*100:.0f}%")
        p2.metric("Prob Touch", f"{t['prob_touch_proxy']*100:.0f}%")
        with p3:
            st.caption(f"📝 {t['notes']}")

        # Score breakdown expander
        with st.expander("Score breakdown"):
            breakdown = get_score_breakdown(t, derived)
            cols = st.columns(6)
            for i, (factor, info) in enumerate(breakdown.items()):
                raw     = info["raw"]
                contrib = info["contrib"]
                val_str = f"{raw:.2f}" if raw is not None else "N/A"
                pts_str = f"{contrib:.1f} pts" if contrib is not None else "—"
                with cols[i % 6]:
                    fcolor = score_color(int(contrib)) if contrib else "#6b7280"
                    st.markdown(
                        f'<div style="text-align:center;padding:8px;'
                        f'border:1px solid #e5e7eb;border-radius:8px">'
                        f'<div style="font-size:11px;color:#6b7280">{factor}</div>'
                        f'<div style="font-size:16px;font-weight:600;color:{fcolor}">'
                        f'{val_str}</div>'
                        f'<div style="font-size:11px;color:{fcolor}">{pts_str}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

        st.divider()


# ─────────────────────────────────────────────
# MAIN APP
# ─────────────────────────────────────────────

def main():
    # Sidebar
    symbol, data_mode, risk_dollars = render_sidebar()

    # Title
    st.title("📊 Options AI Assistant")
    st.caption(
        f"Symbol: **{symbol}** &nbsp;|&nbsp; "
        f"Source: **{data_mode}** &nbsp;|&nbsp; "
        f"Risk budget: **${risk_dollars:,}**"
    )

    # Load data
    with st.spinner(f"Loading {symbol} data from {data_mode}..."):
        try:
            market, chain = load_data(symbol, data_mode)
            market["preferred_risk_dollars"] = risk_dollars
        except Exception as e:
            st.error(f"**Data load failed:** {e}")
            st.info(
                "If using **massive** or **tradier**, make sure your API key is set in "
                "`.streamlit/secrets.toml` (local) or Streamlit Cloud secrets (deployed).\n\n"
                "Switch to **mock** mode in the sidebar to test without an API key."
            )
            return

    # Compute analytics
    derived    = build_derived(market, chain)
    candidates = generate_candidates(market, chain, derived)

    # Market summary
    render_market_summary(market, derived)
    st.markdown("")

    # Chain info
    if chain:
        strikes = sorted(set(r["strike"] for r in chain))
        exps    = sorted(set(r["expiration"] for r in chain))
        st.caption(
            f"Chain: {len(chain)} rows &nbsp;|&nbsp; "
            f"Strikes ${strikes[0]:.0f}–${strikes[-1]:.0f} &nbsp;|&nbsp; "
            f"Expirations: {', '.join(exps)}"
        )

    st.divider()

    # ── Section 2: Market Structure Visuals ──────────────────────────────────
    vis_col1, vis_col2 = st.columns([1, 1])
    with vis_col1:
        render_em_cone(
            spot           = market["spot_price"],
            expected_move  = derived["expected_move"],
            top_trade      = candidates[0] if candidates else None,
            derived        = derived,
        )
    with vis_col2:
        render_gamma_wall(
            chain          = chain,
            spot           = market["spot_price"],
            gamma_flip     = derived.get("gamma_flip"),
            gex_by_strike  = derived.get("gex_by_strike"),
        )

    st.divider()

    # ── Section 3: Strategy Strength ─────────────────────────────────────────
    render_strategy_probability_bars(candidates)

    st.divider()

    # Trade cards
    st.subheader(f"🎯 Top Trade Recommendations")

    if not candidates:
        st.warning(
            "No valid candidates generated. "
            "This can happen when:\n"
            "- Markets are closed (bid/ask = 0)\n"
            "- The chain doesn't have strikes beyond the EM boundary\n"
            "- All candidate spreads produced zero or negative credit\n\n"
            "Try switching to **mock** mode to verify the engine is working."
        )
        return

    top_n = min(len(candidates), 3)
    st.caption(f"{len(candidates)} candidates scored — showing top {top_n}")
    st.markdown("")

    for i, trade in enumerate(candidates[:top_n], start=1):
        render_trade_card(i, trade, derived)

    # Skipped trades
    skipped = [t for t in candidates if t["confidence_score"] < SCORE_TRADABLE]
    if skipped:
        with st.expander(f"Skipped trades ({len(skipped)} below threshold)"):
            for t in skipped:
                label = STRATEGY_LABELS.get(t["strategy_type"], t["strategy_type"])
                st.caption(
                    f"✗ {label} — "
                    f"score {t['confidence_score']}/100 — "
                    f"{t['notes']}"
                )

    # ── Bottom panel: Trade Log + Backtest tabs ───────────────────────────────
    st.divider()
    st.markdown("## 🗂 Tools")
    pos_tab, tlog_tab, bt_tab, analytics_tab, portfolio_tab, optimizer_tab, gov_tab, sys_tab, live_tab = st.tabs([
        "📍 Positions", "📋 Trade Log & Export", "🔬 Backtest",
        "📈 Analytics", "🗃 Portfolio", "🧠 Optimizer", "🛡 Governance", "⚙️ System", "📡 Live Data"
    ])

    with pos_tab:
        # Harvest view (v26) — shows badge, net liq, roll credit, flip rec, analyst + ticket
        import os as _os
        from pathlib import Path as _Path
        from backtest.trade_logger import TradeLogger as _TradeLogger
        if _os.path.exists("/mount/src"):
            _log_path    = _Path("/tmp/options_ai_logs/trade_log.csv")
            _manual_path = _Path("/tmp/options_ai_logs/open_positions.csv")
            _log_dir     = _Path("/tmp/options_ai_logs")
        else:
            _log_path    = _Path("logs/trade_log.csv")
            _manual_path = _Path("data/positions/open_positions.csv")
            _log_dir     = _Path(__file__).parent.parent / "logs"
        _log_dir.mkdir(parents=True, exist_ok=True)
        # Build tracker — supplement with logger's open trades to survive /tmp resets
        _tracker   = PositionTracker(trade_log_path=_log_path, manual_csv_path=_manual_path)
        _tl_logger = _TradeLogger(log_dir=_log_dir)
        _logger_positions = _tl_logger.get_open_trades()
        _snapshot  = _tracker.snapshot(derived=derived, spot=market.get("spot_price", 0))
        # If PositionTracker found nothing but logger has trades, inject them
        if _snapshot["total_open"] == 0 and _logger_positions:
            _snapshot["_injected_positions"] = _logger_positions
            # Re-run snapshot with injected positions as manual overrides
            from position_manager.position_tracker import merge_positions, load_open_from_trade_log
            _merged = merge_positions(load_open_from_trade_log(_log_path), _logger_positions)
            _tracker2 = PositionTracker(trade_log_path=_log_path, manual_csv_path=_manual_path)
            _snapshot = _tracker2.snapshot(derived=derived, spot=market.get("spot_price", 0))
            if _snapshot["total_open"] == 0:
                # Direct injection: treat logger positions as manual CSV rows
                import tempfile as _tf, csv as _csv
                _tmp_manual = _Path(_tf.mktemp(suffix=".csv"))
                if _logger_positions:
                    _fields = list(_logger_positions[0].keys())
                    with open(_tmp_manual, "w", newline="") as _f:
                        _w = _csv.DictWriter(_f, fieldnames=_fields, extrasaction="ignore")
                        _w.writeheader()
                        _w.writerows(_logger_positions)
                _tracker3 = PositionTracker(trade_log_path=_log_path, manual_csv_path=_tmp_manual)
                _snapshot = _tracker3.snapshot(derived=derived, spot=market.get("spot_price", 0))

        # Inject current chain into position rows for live strike selector
        # Chain is indexed by symbol so multi-symbol positions work correctly
        if _snapshot["total_open"] > 0:
            try:
                from providers.provider_factory import build_provider as _bp
                import os as _os3
                _chain_cache: dict = {}
                for _bucket in ("calendar_diagonal", "credit_spreads"):
                    for _prow in _snapshot.get(_bucket, []):
                        _psym = str(_prow.get("symbol","")).upper()
                        if _psym and _psym not in _chain_cache:
                            try:
                                if data_mode == "massive":
                                    _ak = ""
                                    try:
                                        import streamlit as _st3
                                        _ak = _st3.secrets.get("MASSIVE_API_KEY","")
                                    except Exception:
                                        _ak = _os3.getenv("MASSIVE_API_KEY","")
                                    if _ak:
                                        _prov_tmp = _bp("massive", api_key=_ak)
                                        _chain_cache[_psym] = _prov_tmp.get_chain(_psym)
                                elif data_mode == "csv":
                                    _prov_tmp = _bp("csv")
                                    _chain_cache[_psym] = _prov_tmp.get_chain(_psym)
                                else:
                                    _prov_tmp = _bp("mock")
                                    _chain_cache[_psym] = _prov_tmp.get_chain(_psym)
                            except Exception:
                                _chain_cache[_psym] = []
                        _prow["_live_chain"] = _chain_cache.get(_psym, [])
            except Exception:
                pass

        # Enrich positions with live market data for their specific symbol
        # Only when using a live provider (not mock) to avoid stale data
        if data_mode in ("massive",) and _snapshot["total_open"] > 0:
            try:
                from position_manager.position_enricher import enrich_snapshot_with_live_data
                from providers.provider_factory import build_provider
                import os as _os2
                _api_key = ""
                try:
                    import streamlit as _st2
                    _api_key = _st2.secrets.get("MASSIVE_API_KEY","")
                except Exception:
                    _api_key = _os2.getenv("MASSIVE_API_KEY","")
                if _api_key:
                    _live_prov = build_provider("massive", api_key=_api_key)
                    _snapshot  = enrich_snapshot_with_live_data(_snapshot, _live_prov)
            except Exception:
                pass  # enrichment is additive — failure is silent
        _render_harvest_view(_snapshot, market, derived)
        st.divider()
        # Full lifecycle detail below harvest summary
        _render_positions_panel(derived, market)

    with tlog_tab:
        _render_trade_log_panel(candidates, market, derived)

    with bt_tab:
        _render_backtest_panel()

    with analytics_tab:
        _render_analytics_panel()

    with portfolio_tab:
        _render_portfolio_panel()

    with optimizer_tab:
        _render_optimizer_panel()

    with gov_tab:
        _render_governance_panel()

    with sys_tab:
        _render_system_panel()

    with live_tab:
        _render_live_data_panel()


if __name__ == "__main__":
    main()


# ─────────────────────────────────────────────
# TRADE LOG PANEL
# ─────────────────────────────────────────────

def _render_trade_log_panel(ranked: list[dict], market: dict, derived: dict):
    """
    Trade Log tab — visible, always expanded, three sub-tabs.
    """
    import os
    from pathlib import Path
    # Streamlit Cloud is read-only except /tmp — use /tmp for logs there
    if os.path.exists("/mount/src"):
        log_dir = Path("/tmp/options_ai_logs")
    else:
        log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = TradeLogger(log_dir=log_dir)

    log_tab, entry_tab, positions_tab, stats_tab = st.tabs(
        ["📤 Log Scan", "➕ Enter Trade", "📂 Open Positions", "📊 Performance Stats"]
    )

    # ── Log Scan ──────────────────────────────────────────────────────────────
    with log_tab:
        st.markdown("**Log today's AI suggestions**")
        st.caption(
            "Records every suggestion — taken or not. "
            "Builds your strategy accuracy dataset over time."
        )

        if not ranked:
            st.info("Run a live or mock scan first to see candidates here.")
        else:
            for i, t in enumerate(ranked[:3], start=1):
                score  = t.get("confidence_score", 0)
                label  = STRATEGY_LABELS.get(t["strategy_type"], t["strategy_type"])
                tier   = "★ STRONG" if score >= SCORE_STRONG else "○ TRADABLE" if score >= SCORE_TRADABLE else "✗ SKIP"
                col_l, col_no, col_yes = st.columns([4, 1, 1])
                with col_l:
                    st.markdown(f"**#{i} {label}** — {score}/100 {tier}")
                    st.caption(t.get("notes", "")[:80])
                with col_no:
                    if st.button("Log only", key=f"scan_no_{i}", use_container_width=True):
                        scan_id = logger.log_scan(t, market, derived, taken=False)
                        st.success(f"Logged {scan_id}")
                with col_yes:
                    if st.button("Open trade", key=f"scan_yes_{i}", use_container_width=True, type="primary"):
                        scan_id  = logger.log_scan(t, market, derived, taken=True)
                        trade_id = logger.open_trade(t, market, derived)
                        st.success(f"Trade opened: {trade_id}")

        st.divider()
        st.markdown("**Download CSV files**")
        dc1, dc2, dc3 = st.columns(3)

        def _csv_bytes(path):
            if not path.exists() or path.stat().st_size == 0:
                return b"No data yet"
            return path.read_bytes()

        with dc1:
            st.download_button(
                "⬇ trade_log.csv",
                data=_csv_bytes(logger.trade_log_path),
                file_name="trade_log.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with dc2:
            st.download_button(
                "⬇ scan_log.csv",
                data=_csv_bytes(logger.scan_log_path),
                file_name="scan_log.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with dc3:
            st.download_button(
                "⬇ position_monitor.csv",
                data=_csv_bytes(logger.position_mon_path),
                file_name="position_monitor.csv",
                mime="text/csv",
                use_container_width=True,
            )

    # ── Enter Trade ───────────────────────────────────────────────────────────
    with entry_tab:
        _render_trade_entry_form(logger)

    # ── Open Positions ────────────────────────────────────────────────────────
    with positions_tab:
        open_trades = logger.get_open_trades()
        if not open_trades:
            st.info("No open trades yet. Use **Open trade** above after a scan.")
        else:
            st.caption(f"{len(open_trades)} open position(s)")
            for t in open_trades:
                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric(
                        t["strategy_type"].replace("_", " ").title(),
                        f"${t.get('short_strike', '')} / ${t.get('long_strike', t.get('hedge_strike', ''))}",
                    )
                    c2.metric("Entry", f"${t.get('entry_price', '')}")
                    # P&L if current marks are stored
                    _entry_v = abs(float(t.get("entry_price") or 0))
                    _cur_v   = float(t.get("current_spread_value") or t.get("current_value") or 0)
                    if _cur_v > 0 and _entry_v > 0:
                        _contracts = max(1, int(float(t.get("contracts") or 1)))
                        _pnl_est   = round((_cur_v - _entry_v) * 100 * _contracts, 2)
                        c3.metric("Spread", f"${_cur_v:.2f}", delta=f"${_pnl_est:+.0f}",
                                  delta_color="normal")
                    c3.metric("Target", f"${t.get('target_price', '')}")
                    c4.metric("Score", t.get("score", ""))
                    st.caption(
                        f"Opened {t['date_open']} | "
                        f"Exp {t.get('short_expiration', '')} | "
                        f"ID: `{t['trade_id']}`"
                    )
                    with st.expander("✏️ Update marks / Close trade"):
                        _render_close_trade_form(t, logger)

    # ── Stats ─────────────────────────────────────────────────────────────────
    with stats_tab:
        stats = logger.summary_stats()
        if stats["total_trades"] == 0:
            st.info("Stats appear here after your first closed trade.")
        else:
            s1, s2, s3 = st.columns(3)
            s1.metric("Closed Trades", stats["total_trades"])
            s2.metric("Win Rate",
                      f"{stats['win_rate']*100:.1f}%" if stats["win_rate"] is not None else "—")
            s3.metric("Avg P&L",
                      f"${stats['avg_pnl']:.2f}" if stats["avg_pnl"] is not None else "—")
            st.divider()
            if stats["by_strategy"]:
                st.markdown("**By Strategy**")
                for strat, d in stats["by_strategy"].items():
                    wr = f"{d['win_rate']*100:.1f}%" if d["win_rate"] else "—"
                    st.caption(
                        f"**{strat.replace('_',' ').title()}** — "
                        f"{d['trades']} trades | Win rate: {wr} | Avg P&L: ${d['avg_pnl']:.2f}"
                    )


# ─────────────────────────────────────────────
# BACKTEST PANEL
# ─────────────────────────────────────────────

def _render_backtest_panel():
    """
    Backtest tab — run Phase 4 engine from the dashboard.

    Inputs:  symbol, date range, max trades/day, score threshold
    Outputs: performance table, equity curve, by-strategy, by-VGA-environment
    """
    import plotly.graph_objects as go
    from backtest.run_backtest import run_backtest
    from backtest.validation   import all_checks_pass

    st.markdown("**Run a historical backtest using the live strategy engine**")
    st.caption(
        "Requires historical CSV data in `data/historical/`. "
        "Use `backtest/generate_mock_data.py` for test data."
    )

    # ── Config inputs ─────────────────────────────────────────────────────────
    cfg1, cfg2, cfg3, cfg4 = st.columns(4)
    symbol         = cfg1.text_input("Symbol", value="SPY").upper().strip()
    start_date     = cfg2.text_input("Start date", value="2025-03-10")
    end_date       = cfg3.text_input("End date",   value="2025-04-18")
    score_thresh   = cfg4.number_input("Min score", value=65, min_value=0, max_value=100, step=5)

    cfg5, cfg6 = st.columns([1, 3])
    max_per_day    = cfg5.number_input("Max trades/day", value=1, min_value=1, max_value=5, step=1)
    starting_cap   = cfg6.number_input("Starting capital ($)", value=100_000, step=1_000)

    run_btn = st.button("▶ Run Backtest", type="primary", use_container_width=False)

    if not run_btn:
        st.info("Configure parameters above and click **Run Backtest**.")
        return

    # ── Run ───────────────────────────────────────────────────────────────────
    with st.spinner(f"Running backtest: {symbol} {start_date} → {end_date}…"):
        try:
            result = run_backtest(
                symbols            = [symbol],
                start              = start_date,
                end                = end_date,
                starting_capital   = float(starting_cap),
                max_trades_per_day = int(max_per_day),
                score_threshold    = int(score_thresh),
            )
        except FileNotFoundError as e:
            st.error(
                f"Historical data not found: `{e}`\n\n"
                f"Run `python backtest/generate_mock_data.py` to generate mock data, "
                f"or add real CSV files to `data/historical/`."
            )
            return
        except Exception as e:
            st.error(f"Backtest error: {e}")
            return

    st.success("Backtest complete")

    st.divider()

    # ── Validation status ─────────────────────────────────────────────────────
    vl      = result.get("validation", [])
    passed  = result.get("passed")
    n_pass  = sum(1 for _, ok in vl if ok)
    n_total = len(vl)

    if passed:
        st.caption(f"✅ {n_pass}/{n_total} validation checks passed")
    else:
        fails = [n for n, ok in vl if not ok]
        st.warning(f"⚠️ {n_pass}/{n_total} checks passed — failures: {', '.join(fails[:5])}")

    # ── Top-line metrics ──────────────────────────────────────────────────────
    st.markdown("### 📊 Performance Summary")
    pf   = result["performance"]
    eq_s = result["equity_summary"]
    st_  = result["simulated_trades"]

    total_pnl = sum(t["pnl"] for t in st_)

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Trades",       pf["total_trades"])
    m2.metric("Win Rate",     f"{pf['win_rate']*100:.1f}%")
    m3.metric("Expectancy",   f"${pf['expectancy']:.2f}")
    m4.metric("Profit Factor",
              f"{pf['profit_factor']:.2f}" if pf["profit_factor"] != float("inf") else "∞")
    m5.metric("Max Drawdown", f"{pf['max_drawdown']*100:.1f}%")
    m6.metric("Total P&L",    f"${total_pnl:.2f}",
              delta=f"${eq_s['net_profit']:.2f} net")

    m7, m8, m9 = st.columns(3)
    m7.metric("Sharpe",        f"{pf['sharpe']:.2f}")
    m8.metric("Sortino",
              f"{pf['sortino']:.2f}" if pf["sortino"] != float("inf") else "∞")
    m9.metric("Avg Days Held", f"{pf['average_days_held']:.1f}")

    # ── Equity curve ──────────────────────────────────────────────────────────
    eq = result["equity_curve"]
    if eq:
        st.markdown("### 📈 Equity Curve")
        dates   = [p["date"]   for p in eq]
        equities = [p["equity"] for p in eq]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=dates, y=equities,
            mode="lines+markers",
            line=dict(color="#22c55e", width=2),
            marker=dict(size=5),
            name="Equity",
            hovertemplate="%{x}<br>$%{y:,.2f}<extra></extra>",
        ))
        fig.add_hline(
            y=eq_s["starting_capital"],
            line_dash="dash", line_color="#6b7280",
            annotation_text=f"Start ${eq_s['starting_capital']:,.0f}",
        )
        fig.update_layout(
            height=280,
            margin=dict(l=0, r=0, t=20, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e5e7eb"),
            xaxis=dict(gridcolor="#374151"),
            yaxis=dict(gridcolor="#374151", tickprefix="$"),
        )
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ── Report tabs ───────────────────────────────────────────────────────────
    rp = result["reports"]
    r1, r2, r3, r4 = st.tabs(
        ["By Strategy", "By VGA Environment", "By IV Regime", "By Gamma Regime"]
    )

    def _report_table(report_dict: dict):
        if not report_dict:
            st.caption("No data.")
            return
        rows = []
        for label, d in report_dict.items():
            rows.append({
                "Group":         label.replace("_", " ").title(),
                "Trades":        d.get("trades", 0),
                "Win Rate":      f"{d['win_rate']*100:.1f}%" if d.get("win_rate") is not None else "—",
                "Expectancy":    f"${d.get('expectancy', 0):.2f}",
                "Profit Factor": f"{d['profit_factor']:.2f}" if d.get("profit_factor") not in (None, float("inf")) else "∞",
                "Avg Days":      f"{d.get('average_days_held', 0):.1f}",
                "Total P&L":     f"${d.get('total_pnl', 0):.2f}",
            })
        import pandas as pd
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    with r1:
        _report_table(rp.get("by_strategy", {}))
    with r2:
        _report_table(rp.get("by_environment", {}))
    with r3:
        _report_table(rp["by_regime"].get("iv_regime", {}))
    with r4:
        _report_table(rp["by_regime"].get("gamma_regime", {}))

    st.divider()

    # ── Raw trade log ─────────────────────────────────────────────────────────
    with st.expander(f"Raw simulated trades ({len(st_)})"):
        if st_:
            import pandas as pd
            display_cols = [
                "trade_id", "strategy_type", "entry_date", "exit_date",
                "entry_price", "exit_price", "pnl", "return_pct",
                "exit_reason", "days_held", "vga_environment", "score",
            ]
            df = pd.DataFrame(st_)[[c for c in display_cols if c in df.columns if c in df.columns]]
            df2 = pd.DataFrame([{c: t.get(c, "") for c in display_cols} for t in st_])
            st.dataframe(df2, use_container_width=True, hide_index=True)

        # Download button
        import io, csv as _csv
        if st_:
            buf = io.StringIO()
            w = _csv.DictWriter(buf, fieldnames=list(st_[0].keys()))
            w.writeheader()
            w.writerows(st_)
            st.download_button(
                "⬇ Download backtest results CSV",
                data=buf.getvalue().encode(),
                file_name=f"backtest_{symbol}_{start_date}_{end_date}.csv",
                mime="text/csv",
                use_container_width=False,
            )


# ─────────────────────────────────────────────
# POSITIONS PANEL
# ─────────────────────────────────────────────

def _render_positions_panel(derived: dict, market: dict) -> None:
    """
    📍 Positions tab — tracks open trades, surfaces lifecycle signals.

    Primary source: logs/trade_log.csv (rows where date_close is blank)
    Fallback/override: data/positions/open_positions.csv
    """
    import os
    from pathlib import Path

    # Cloud-safe path resolution
    if os.path.exists("/mount/src"):
        log_path    = Path("/tmp/options_ai_logs/trade_log.csv")
        manual_path = Path("/tmp/options_ai_logs/open_positions.csv")
    else:
        log_path    = Path("logs/trade_log.csv")
        manual_path = Path("data/positions/open_positions.csv")

    tracker  = PositionTracker(trade_log_path=log_path, manual_csv_path=manual_path)
    spot     = market.get("spot_price", 0)
    snapshot = tracker.snapshot(derived=derived, spot=spot)
    # Fallback: if tracker found nothing, try reading from TradeLogger directly
    if snapshot["total_open"] == 0:
        try:
            from backtest.trade_logger import TradeLogger as _TL
            import tempfile as _tf2, csv as _csv2
            from pathlib import Path as _P2
            _tl2 = _TL(log_dir=log_path.parent)
            _open2 = _tl2.get_open_trades()
            if _open2:
                _tmp2 = _P2(_tf2.mktemp(suffix=".csv"))
                _fields2 = list(_open2[0].keys())
                with open(_tmp2, "w", newline="") as _f2:
                    _w2 = _csv2.DictWriter(_f2, fieldnames=_fields2, extrasaction="ignore")
                    _w2.writeheader(); _w2.writerows(_open2)
                snapshot = PositionTracker(trade_log_path=log_path,
                                           manual_csv_path=_tmp2).snapshot(derived=derived, spot=spot)
        except Exception:
            pass
    summary  = snapshot["summary"]

    # ── Summary bar ───────────────────────────────────────────────────────────
    s1, s2, s3, s4, s5 = st.columns(5)
    s1.metric("Open Positions", summary["total_positions"])
    s2.metric("🔴 High Urgency",   summary["high_urgency"],
              delta="Action required" if summary["high_urgency"] else None,
              delta_color="inverse" if summary["high_urgency"] else "off")
    s3.metric("🟡 Medium Urgency", summary["medium_urgency"])
    s4.metric("⚠️ Close Signals",  summary["close_signals"])
    s5.metric("VGA",               summary["vga_environment"].replace("_", " ").title())

    if summary["total_positions"] == 0:
        st.info(
            "No open positions found.\n\n"
            "Open positions are read automatically from `logs/trade_log.csv` "
            "(rows where date_close is blank).\n\n"
            "Use **📋 Trade Log → Open trade** to log a new position, "
            "or add rows to `data/positions/open_positions.csv` for manual override."
        )
        return

    st.divider()

    # ── Calendar / Diagonal positions ─────────────────────────────────────────
    cal_diag = snapshot["calendar_diagonal"]
    if cal_diag:
        st.markdown("### 📅 Calendars & Diagonals")
        for pos in cal_diag:
            decision = pos.get("decision", {})
            action   = decision.get("action", "HOLD")
            urgency  = decision.get("urgency", "LOW")

            urgency_color = {"HIGH": "#ef4444", "MEDIUM": "#f59e0b", "LOW": "#22c55e"}.get(urgency, "#6b7280")
            action_color  = {"EXIT_ENVIRONMENT": "#ef4444", "EXIT_LONG_WINDOW": "#ef4444",
                             "EXIT_STRUCTURE_BREAK": "#ef4444", "CONVERT_TO_DIAGONAL": "#f97316",
                             "ROLL_SHORT": "#f59e0b", "ROLL_DIAGONAL_SHORT": "#f59e0b",
                             "HOLD": "#22c55e"}.get(action, "#6b7280")

            with st.container(border=True):
                h1, h2, h3, h4 = st.columns([3, 2, 2, 2])
                st.markdown(
                    f'<span style="background:{action_color}20;color:{action_color};'
                    f'padding:3px 12px;border-radius:10px;font-size:13px;font-weight:700;'
                    f'border:1px solid {action_color}40">{action.replace("_"," ")}</span>'
                    f'&nbsp;&nbsp;<span style="color:{urgency_color};font-size:12px">'
                    f'● {urgency}</span>',
                    unsafe_allow_html=True,
                )
                m1, m2, m3, m4, m5 = st.columns(5)
                m1.metric("Symbol",     pos.get("symbol", ""))
                m2.metric("Structure",  pos.get("strategy_type", "").replace("_", " ").title())
                m3.metric("Long Strike", f"${decision.get('long_strike', pos.get('long_strike', ''))}")
                m4.metric("Short Strike",f"${decision.get('short_strike', pos.get('short_strike', ''))}")
                m5.metric("Long DTE",    f"{decision.get('long_dte', pos.get('long_dte', ''))}")

                st.caption(f"📝 {decision.get('rationale', '')}")

                if decision.get("target_short_strike"):
                    st.caption(
                        f"→ Target short strike: ${decision['target_short_strike']} | "
                        f"Target short DTE: {decision.get('target_short_dte', '')} | "
                        f"Notes: {decision.get('notes', '')}"
                    )

                with st.expander("Full decision details"):
                    st.json(decision)

    # ── Credit spreads ────────────────────────────────────────────────────────
    credit_sp = snapshot["credit_spreads"]
    if credit_sp:
        st.divider()
        st.markdown("### 💰 Credit Spreads")
        for pos in credit_sp:
            status = pos.get("management_status", "HOLD")
            status_color = {"CLOSE_STOP": "#ef4444", "CLOSE_TIME": "#f59e0b",
                            "CLOSE_TP": "#22c55e", "REVIEW_OR_ROLL": "#f97316",
                            "HOLD": "#6b7280"}.get(status, "#6b7280")
            with st.container(border=True):
                st.markdown(
                    f'<span style="background:{status_color}20;color:{status_color};'
                    f'padding:3px 12px;border-radius:10px;font-size:13px;font-weight:700;'
                    f'border:1px solid {status_color}40">{status.replace("_"," ")}</span>',
                    unsafe_allow_html=True,
                )
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Symbol",        pos.get("symbol", ""))
                c2.metric("Strategy",      pos.get("strategy_type", "").replace("_"," ").title())
                c3.metric("Short Strike",  f"${pos.get('short_strike','')}")
                c4.metric("Expiration",    pos.get("short_expiration", ""))

    # ── Debit spreads ─────────────────────────────────────────────────────────
    debit_sp = snapshot["debit_spreads"]
    if debit_sp:
        st.divider()
        st.markdown("### 📈 Debit Spreads")
        for pos in debit_sp:
            status = pos.get("management_status", "HOLD")
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Symbol",     pos.get("symbol", ""))
                c2.metric("Strategy",   pos.get("strategy_type", "").replace("_"," ").title())
                c3.metric("Status",     status)
                c4.metric("Expiration", pos.get("short_expiration", ""))

    # ── Manual override instructions ──────────────────────────────────────────
    with st.expander("ℹ️ How position tracking works"):
        st.markdown("""
**Primary source:** `logs/trade_log.csv` — any row where `date_close` is blank is treated as open.

**Manual override:** `data/positions/open_positions.csv`
- Rows with a matching `trade_id` **override** the log row
- Rows without a `trade_id` are **appended** as supplemental positions

**CSV column reference for manual positions:**
```
trade_id, symbol, strategy_type, direction,
short_strike, long_strike, short_expiration, long_expiration,
short_dte, long_dte, entry_price, spot_open
```
        """)


# ─────────────────────────────────────────────
# ANALYTICS PANEL
# ─────────────────────────────────────────────

def _render_analytics_panel() -> None:
    """
    📈 Analytics tab — reads backtest_events.csv + backtest_runs.csv
    and renders win rate, expectancy, rejection analysis, and regime performance.
    """
    import os
    from pathlib import Path
    from backtest.metrics_reader import (
        load_events, load_runs, summary_stats,
        by_symbol, by_regime, rejection_reasons, by_strategy,
        selection_rate_by_regime,
    )

    # Cloud-safe paths
    if os.path.exists("/mount/src"):
        events_path = "/tmp/options_ai_logs/backtest_events.csv"
        runs_path   = "/tmp/options_ai_logs/backtest_runs.csv"
    else:
        events_path = "logs/backtest_events.csv"
        runs_path   = "logs/backtest_runs.csv"

    events_df = load_events(events_path)
    runs_df   = load_runs(runs_path)

    if events_df.empty:
        st.info(
            "No analytics data yet.\n\n"
            "Analytics are populated automatically every time the engine runs "
            "with `log_backtest_events=True`. Run the backtest tab or the portfolio "
            "runner to start building your dataset."
        )
        return

    st.markdown("### 📊 Event Summary")
    stats = summary_stats(events_df)
    s1, s2, s3, s4, s5, s6, s7, s8 = st.columns(8)
    s1.metric("Total Events",      stats["total_events"])
    s2.metric("Ranked",            stats["ranked_trades"])
    s3.metric("Selected",          stats["selected_trades"])
    s4.metric("Rejected",          stats["rejected_trades"])
    s5.metric("Position Actions",  stats["position_actions"])
    s6.metric("Avg Ranked Score",  stats["avg_ranked_score"])
    s7.metric("Avg Selected Score",stats["avg_selected_score"])
    s8.metric("Est. Position P&L", f"${stats['estimated_position_pnl']:.2f}")

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**By Symbol**")
        sym_df = by_symbol(events_df)
        if not sym_df.empty:
            st.dataframe(sym_df, use_container_width=True, hide_index=True)

        st.markdown("**By VGA Regime**")
        regime_df = by_regime(events_df)
        if not regime_df.empty:
            st.dataframe(regime_df, use_container_width=True, hide_index=True)

    with col2:
        st.markdown("**Rejection Reasons**")
        rej_df = rejection_reasons(events_df)
        if not rej_df.empty:
            st.dataframe(rej_df, use_container_width=True, hide_index=True)
        else:
            st.caption("No rejections logged yet.")

        st.markdown("**Selection Rate by Regime**")
        rate_df = selection_rate_by_regime(events_df)
        if not rate_df.empty:
            st.dataframe(rate_df, use_container_width=True, hide_index=True)

    st.divider()

    st.markdown("**By Strategy**")
    strat_df = by_strategy(events_df)
    if not strat_df.empty:
        st.dataframe(strat_df, use_container_width=True, hide_index=True)

    # Run history
    if not runs_df.empty:
        st.divider()
        st.markdown("**Portfolio Run History**")
        st.dataframe(runs_df.tail(20), use_container_width=True, hide_index=True)

    # Download buttons
    st.divider()
    st.markdown("**Download Raw Data**")
    dc1, dc2 = st.columns(2)
    with dc1:
        st.download_button(
            "⬇ backtest_events.csv",
            data=open(events_path, "rb").read() if Path(events_path).exists() else b"",
            file_name="backtest_events.csv", mime="text/csv",
            use_container_width=True,
        )
    with dc2:
        if Path(runs_path).exists():
            st.download_button(
                "⬇ backtest_runs.csv",
                data=open(runs_path, "rb").read(),
                file_name="backtest_runs.csv", mime="text/csv",
                use_container_width=True,
            )


# ─────────────────────────────────────────────
# PORTFOLIO RUNNER PANEL (for multi-symbol runs)
# ─────────────────────────────────────────────

def _render_portfolio_panel() -> None:
    """Inline portfolio runner — runs multi-symbol engine from the dashboard."""
    from engines.portfolio_runner import run_portfolio_engine
    from data.mock_data import load_mock_market, build_mock_chain

    st.markdown("**Multi-symbol portfolio run**")
    st.caption("Runs the full engine across symbols, allocates risk, and surfaces roll + alert signals.")

    symbols_input = st.text_input("Symbols (comma-separated)", value="SPY", key="portfolio_symbols")
    col1, col2, col3 = st.columns(3)
    log_events  = col1.checkbox("Log backtest events", value=False, key="portfolio_log_events")
    log_journal = col2.checkbox("Log execution journal", value=False, key="portfolio_log_journal")
    log_alerts  = col3.checkbox("Log alerts CSV", value=False, key="portfolio_log_alerts")

    if not st.button("▶ Run Portfolio Engine", type="primary", key="portfolio_run_btn"):
        st.info("Configure and click Run.")
        return

    symbols = [s.strip().upper() for s in symbols_input.split(",") if s.strip()]
    payloads = []
    for sym in symbols:
        # Use mock data — replace with live provider call here
        m = load_mock_market()
        m["symbol"] = sym
        payloads.append({"symbol": sym, "market": m, "chain": build_mock_chain()})

    with st.spinner("Running portfolio engine…"):
        output = run_portfolio_engine(
            payloads,
            log_backtest_events=log_events,
            log_execution_journal=log_journal,
            log_alerts=log_alerts,
        )

    meta  = output["portfolio_meta"]
    alloc = output["allocation"]

    # Summary metrics
    m1,m2,m3,m4,m5,m6 = st.columns(6)
    m1.metric("Symbols",   meta["symbols_processed"])
    m2.metric("Ranked",    meta["total_ranked_trades"])
    m3.metric("Selected",  meta["selected_trades"])
    m4.metric("Rejected",  meta["rejected_trades"])
    m5.metric("Open Pos",  meta["total_open_positions"])
    m6.metric("Budget Used", f"${alloc['used_risk_budget']:,.0f}")

    st.divider()

    # Alerts panel
    alerts = output.get("alerts", [])
    if alerts:
        from engines.alert_router import _SEV_ORDER
        high_alerts = [a for a in alerts if _SEV_ORDER.get(a.get("severity","INFO"),0) >= 3]
        if high_alerts:
            st.markdown("#### 🔴 High Priority Alerts")
            for a in high_alerts[:5]:
                st.error(f"**{a['title']}** — {a['message']}")
        med_alerts = [a for a in alerts if _SEV_ORDER.get(a.get("severity","INFO"),0) == 2]
        if med_alerts:
            st.markdown("#### 🟡 Medium Priority")
            for a in med_alerts[:5]:
                st.warning(f"**{a['title']}** — {a['message']}")

    st.divider()

    # Roll suggestions
    rolls = output.get("roll_suggestions", [])
    if rolls:
        st.markdown("#### 📋 Roll Suggestions")
        for r in rolls:
            action  = r.get("action","HOLD")
            urgency = r.get("urgency","LOW")
            color   = {"HIGH":"🔴","MEDIUM":"🟡","LOW":"🟢"}.get(urgency,"⚪")
            st.markdown(
                f"{color} **{r.get('symbol','')} {r.get('strategy','').replace('_',' ').title()}** "
                f"→ `{action}` — {r.get('rationale','')[:80]}"
            )

    st.divider()

    # Selected trades
    selected = alloc.get("selected_trades", [])
    if selected:
        st.markdown("#### ✅ Selected Trades")
        for t in selected:
            st.markdown(
                f"**{t.get('symbol','')} {str(t.get('strategy_type',t.get('strategy',''))).replace('_',' ').title()}** "
                f"score={t.get('confidence_score',t.get('score',0)):.0f} | "
                f"risk=${t.get('_risk',0):.0f} | "
                f"contracts={t.get('contracts',1)}"
            )

    # ── Lifecycle signals from open cal/diag positions ───────────────────────
    for sym_block in output.get("symbols", []):
        eng = sym_block.get("engine_output", {})
        lifecycle = eng.get("positions", {}).get("calendar_diagonal_lifecycle", [])
        if lifecycle:
            st.divider()
            st.caption(f"📅 {sym_block['symbol']} calendar/diagonal lifecycle:")
            _render_lifecycle_signals(eng.get("positions", {}))

    # Raw output expander
    with st.expander(f"Raw output — {meta['run_id']}"):
        st.json(meta)


# ─────────────────────────────────────────────
# OPTIMIZER PANEL
# ─────────────────────────────────────────────

def _render_optimizer_panel() -> None:
    """🧠 Optimizer tab — strategy outcomes, rejection diagnostics, allocation recommendations."""
    import os
    from engines.optimizer_report import build_optimizer_report

    if os.path.exists("/mount/src"):
        bt_path  = "/tmp/options_ai_logs/backtest_events.csv"
        ex_path  = "/tmp/options_ai_logs/execution_journal.csv"
        roll_path = "/tmp/options_ai_logs/roll_suggestions.csv"
        snap_dir  = "/tmp/options_ai_snapshots"
    else:
        bt_path   = "logs/backtest_events.csv"
        ex_path   = "logs/execution_journal.csv"
        roll_path = "logs/roll_suggestions.csv"
        snap_dir  = "snapshots"

    report  = build_optimizer_report(
        backtest_events_path=bt_path,
        execution_journal_path=ex_path,
        roll_log_path=roll_path,
        snapshots_dir=snap_dir,
    )
    summary = report["summary"]

    # ── Summary cards ─────────────────────────────────────────────────────────
    best_s = summary.get("best_strategy", {})
    top_r  = summary.get("dominant_rejection_reason", {})
    top_sym = summary.get("best_symbol_candidate", {})

    c1, c2, c3 = st.columns(3)
    c1.metric("Best Strategy",    best_s.get("strategy","—"),
              delta=f"expectancy ${best_s.get('expectancy',0):.2f}" if best_s else None)
    c2.metric("Top Rejection",    top_r.get("reject_reason", top_r.get("reason","—")),
              delta=f"{top_r.get('count',0)} occurrences" if top_r else None)
    c3.metric("Best Symbol",      top_sym.get("symbol","—"),
              delta=top_sym.get("allocation_action","—") if top_sym else None)

    st.divider()

    # ── Tables ────────────────────────────────────────────────────────────────
    tabs = st.tabs([
        "Strategy Outcomes", "Rejection Reasons",
        "Roll Patterns", "Symbol Allocation", "Snapshot Trend",
    ])

    sections = [
        report["strategy_outcomes"],
        report["rejection_reasons"],
        report["roll_actions"],
        report["symbol_allocation"],
        report["snapshot_changes"],
    ]

    for tab, df in zip(tabs, sections):
        with tab:
            if df is None or df.empty:
                st.info("No data yet — run the engine with logging enabled to populate this panel.")
            else:
                st.dataframe(df, use_container_width=True, hide_index=True)

    # ── Parameter Tuner + Patcher inline ────────────────────────────────────
    _render_tuner_patcher_inline(bt_path, ex_path, roll_path)

    # ── Session compare ───────────────────────────────────────────────────────
    st.divider()
    st.markdown("### 🔍 Session Compare")

    try:
        from engines.snapshot_manager import SnapshotManager
        from engines.session_compare import compare_portfolio_snapshots

        mgr   = SnapshotManager(base_dir=snap_dir)
        items = mgr.list_snapshots(category="portfolio", limit=20)

        if len(items) < 2:
            st.caption("Need at least 2 portfolio snapshots. Run the Portfolio tab with snapshot_history=True.")
        else:
            labels = [i["filename"] for i in items]
            col1, col2 = st.columns(2)
            with col1:
                old_idx = st.selectbox("Older", range(len(labels)),
                                       index=min(1, len(labels)-1),
                                       format_func=lambda i: labels[i],
                                       key="opt_old")
            with col2:
                new_idx = st.selectbox("Newer", range(len(labels)),
                                       index=0,
                                       format_func=lambda i: labels[i],
                                       key="opt_new")

            comparison = compare_portfolio_snapshots(
                mgr.load_snapshot(items[old_idx]["path"]),
                mgr.load_snapshot(items[new_idx]["path"]),
            )

            st.markdown(f"**Old:** `{comparison['old_run_id']}` → **New:** `{comparison['new_run_id']}`")

            md = comparison.get("meta_delta", {})
            if md:
                cols = st.columns(min(len(md), 4))
                for i, (field, vals) in enumerate(md.items()):
                    delta = vals.get("delta", 0)
                    cols[i % 4].metric(
                        field.replace("_", " ").title(),
                        vals.get("new", "—"),
                        delta=f"{delta:+.2f}" if delta else None,
                    )

            for section, data in [
                ("Selected Trades", comparison["selected_trades"]),
                ("Roll Suggestions", comparison["roll_suggestions"]),
            ]:
                added   = data.get("added", [])
                removed = data.get("removed", [])
                changed = data.get("changed", [])
                if any([added, removed, changed]):
                    with st.expander(f"{section} — {len(added)} added, {len(removed)} removed, {len(changed)} changed"):
                        if added:
                            st.markdown("**Added:**")
                            st.json([{k: v for k, v in t.items() if k in
                                      ("symbol","strategy_type","strategy","confidence_score","decision")}
                                     for t in added[:5]])
                        if changed:
                            st.markdown("**Changed:**")
                            st.json(changed[:5])

    except Exception as e:
        st.caption(f"Session compare unavailable: {e}")


# ─────────────────────────────────────────────
# TUNER + PATCHER PANEL (appended to Optimizer tab)
# ─────────────────────────────────────────────

def _render_tuner_patcher_inline(bt_path: str, ex_path: str, roll_path: str) -> None:
    """
    Inline parameter tuner + config patcher sections.
    Called from _render_optimizer_panel() after the optimizer tables.
    """
    st.divider()
    st.markdown("### 🎛 Parameter Tuner")
    st.caption("Suggestions based on log behavior. Review before applying.")

    from engines.parameter_tuner import tune_parameters

    try:
        tuning = tune_parameters(
            backtest_events_path=bt_path,
            execution_journal_path=ex_path,
            roll_log_path=roll_path,
        )
        payload = tuning.to_dict()
    except Exception as e:
        st.caption(f"Tuner unavailable: {e}")
        return

    summary = payload.get("summary", {})
    s1, s2, s3 = st.columns(3)
    s1.metric("Sel/Rej Ratio",     summary.get("selected_rejected_ratio", "—"))
    s2.metric("Top Rejection",     summary.get("top_rejection_reason", "—") or "—")
    s3.metric("Top Roll Action",   summary.get("top_roll_action", "—") or "—")

    suggestions = payload.get("suggestions", [])
    if not suggestions:
        st.caption("No parameter suggestions yet — run more engine cycles with logging enabled.")
        return

    for s in suggestions:
        conf = float(s.get("confidence", 0))
        col  = "#22c55e" if conf >= 0.70 else ("#f59e0b" if conf >= 0.55 else "#6b7280")
        st.markdown(
            f'<div style="background:#0f1117;border:1px solid {col}33;border-radius:10px;padding:12px;margin-bottom:8px">'
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

    st.divider()
    st.markdown("### 🛠 Config Patcher")
    st.caption("Apply approved tuner suggestions to `config.yaml`. Always creates a backup.")

    option_labels = [
        f'{s["parameter"]} → {s["suggested_value"]} ({int(float(s.get("confidence",0))*100)}%)'
        for s in suggestions
    ]
    selected = st.multiselect("Parameters to patch", option_labels, default=option_labels,
                               key="patcher_params")
    selected_params = [s["parameter"] for s, lbl in zip(suggestions, option_labels) if lbl in selected]
    min_conf = st.slider("Min confidence", 0.0, 1.0, 0.65, 0.05, key="patcher_conf")

    from engines.config_patcher import preview_config_patch, apply_config_patch

    import os
    cfg_path    = "config/config.yaml"
    backup_dir  = "/tmp/options_ai_config_backups" if os.path.exists("/mount/src") else "config_backups"

    col1, col2 = st.columns(2)
    with col1:
        if st.button("👁 Preview", key="patcher_preview"):
            result = preview_config_patch(
                config_path=cfg_path,
                tuning_payload=payload,
                include_parameters=selected_params,
                min_confidence=min_conf,
            )
            st.json(result.to_dict(), expanded=False)

    with col2:
        if st.button("✅ Apply Patch", type="primary", key="patcher_apply"):
            result = apply_config_patch(
                config_path=cfg_path,
                tuning_payload=payload,
                include_parameters=selected_params,
                min_confidence=min_conf,
                make_backup=True,
                backup_dir=backup_dir,
            )
            if result.applied:
                st.success(f"Config updated. {result.notes}")
            else:
                st.info(f"No changes applied. {result.notes}")
            st.json(result.to_dict(), expanded=False)


# ─────────────────────────────────────────────
# GOVERNANCE PANEL
# ─────────────────────────────────────────────

def _render_governance_panel() -> None:
    """🛡 Governance tab — policy table, approval queue, change audit."""
    import os
    from engines.governance_guard import build_governance_policy_summary, evaluate_patch_payload
    from engines.parameter_tuner import tune_parameters
    from engines.approval_queue import ApprovalQueue
    from engines.change_audit import ChangeAudit
    from engines.config_patcher import (
        load_config, build_tuning_payload_from_queue_requests, apply_config_patch,
    )

    cfg_path   = "config/config.yaml"
    queue_path = "/tmp/options_ai_logs/approval_queue.csv" if os.path.exists("/mount/src") else "logs/approval_queue.csv"
    audit_path = "/tmp/options_ai_logs/change_audit.csv"  if os.path.exists("/mount/src") else "logs/change_audit.csv"
    bt_path    = "/tmp/options_ai_logs/backtest_events.csv"   if os.path.exists("/mount/src") else "logs/backtest_events.csv"
    ex_path    = "/tmp/options_ai_logs/execution_journal.csv" if os.path.exists("/mount/src") else "logs/execution_journal.csv"
    roll_path  = "/tmp/options_ai_logs/roll_suggestions.csv"  if os.path.exists("/mount/src") else "logs/roll_suggestions.csv"
    backup_dir = "/tmp/options_ai_config_backups" if os.path.exists("/mount/src") else "config_backups"

    # ── Policy table ──────────────────────────────────────────────────────────
    st.markdown("### 📋 Governance Policy")
    policy = build_governance_policy_summary()
    st.dataframe(policy, use_container_width=True, hide_index=True)

    # ── Approval queue ────────────────────────────────────────────────────────
    st.divider()
    st.markdown("### ✅ Approval Queue")

    queue = ApprovalQueue(path=queue_path)
    pending  = queue.pending_requests()
    approved = queue.approved_requests()

    c1, c2 = st.columns(2)
    c1.metric("Pending",  len(pending))
    c2.metric("Approved", len(approved))

    if st.button("🔄 Generate New Requests from Tuner", key="gov_generate"):
        try:
            cfg        = load_config(cfg_path)
            tuning     = tune_parameters(
                backtest_events_path=bt_path,
                execution_journal_path=ex_path,
                roll_log_path=roll_path,
            )
            payload    = tuning.to_dict()
            governed   = evaluate_patch_payload(config=cfg, tuning_payload=payload)
            created    = queue.create_many_from_governed_suggestions(
                governance_payload=governed, approved_only=True,
                source_run_id="dashboard_manual",
            )
            st.success(f"Staged {len(created)} governance-approved request(s) into queue.")
            st.rerun()
        except Exception as e:
            st.error(f"Could not generate requests: {e}")

    if pending:
        st.markdown("**Pending requests:**")
        for item in pending:
            with st.container():
                col_left, col_right = st.columns([3,1])
                with col_left:
                    st.markdown(
                        f'`{item.get("parameter","—")}` '
                        f'`{item.get("current_value","—")}` → '
                        f'`{item.get("requested_value","—")}` '
                        f'({int(float(item.get("confidence",0))*100)}% conf)'
                    )
                    st.caption(item.get("rationale",""))
                with col_right:
                    reviewer_name = st.text_input("Reviewer", key=f"gov_rev_{item['request_id']}", label_visibility="collapsed", placeholder="Reviewer")
                    a_col, r_col = st.columns(2)
                    if a_col.button("✓", key=f"gov_approve_{item['request_id']}", help="Approve"):
                        queue.approve(item["request_id"], reviewer=reviewer_name)
                        st.rerun()
                    if r_col.button("✗", key=f"gov_reject_{item['request_id']}", help="Reject"):
                        queue.reject(item["request_id"], reviewer=reviewer_name)
                        st.rerun()

    # ── Apply approved queue ──────────────────────────────────────────────────
    if approved:
        st.markdown("**Approved — ready to apply:**")
        for item in approved:
            st.markdown(f"✅ `{item.get('parameter','—')}` → `{item.get('requested_value','—')}`"
                        f" (approved by `{item.get('reviewer','—')}`)")

        reviewer_apply = st.text_input("Your name (for audit log)", key="gov_reviewer_apply")
        if st.button("⚡ Apply Approved Queue to Config", type="primary", key="gov_apply"):
            payload  = build_tuning_payload_from_queue_requests(approved)
            result   = apply_config_patch(
                config_path=cfg_path, tuning_payload=payload,
                include_parameters=[x["parameter"] for x in approved],
                min_confidence=0.0, make_backup=True, backup_dir=backup_dir,
                enforce_governance=True, audit_log=True, audit_path=audit_path,
                source="queue", reviewer=reviewer_apply,
            )
            if result.applied:
                for req in approved:
                    queue.mark_applied(req["request_id"], reviewer=reviewer_apply,
                                       review_notes="Applied via governance panel.")
                st.success(f"Applied. Notes: {result.notes}")
            else:
                st.info(f"No changes. Notes: {result.notes}")
            st.json(result.to_dict(), expanded=False)

    # ── Change audit ──────────────────────────────────────────────────────────
    st.divider()
    st.markdown("### 📜 Change Audit Log")

    audit  = ChangeAudit(path=audit_path)
    summary = audit.summary()
    a1, a2, a3 = st.columns(3)
    a1.metric("Total Changes",    summary.get("total_changes", 0))
    a2.metric("Last Change",      str(summary.get("last_change","—"))[:19] if summary.get("last_change") else "—")
    a3.metric("Reviewers",        len(summary.get("reviewers",[])))

    rows = audit.load()
    if rows:
        import pandas as pd
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button(
            "⬇ change_audit.csv", data=open(audit_path,"rb").read() if os.path.exists(audit_path) else b"",
            file_name="change_audit.csv", mime="text/csv", use_container_width=True,
        )
    else:
        st.caption("No changes logged yet — apply a config patch to start the audit trail.")


# ─────────────────────────────────────────────
# SYSTEM PANEL — health check + bootstrap + deployment packet + release manifest
# ─────────────────────────────────────────────

def _render_system_panel() -> None:
    """⚙️ System tab — health check, bootstrap, deployment packet, release manifest."""
    import os
    import tempfile
    from engines.health_check import run_health_check
    from engines.bootstrap import bootstrap_environment

    cfg_path  = "config/config.yaml"
    pkt_dir   = "/tmp/options_ai_packets" if os.path.exists("/mount/src") else "deployment_packets"

    STATUS_COLORS = {"PASS":"#22c55e","WARN":"#f59e0b","FAIL":"#ef4444"}

    # ── Health Check ─────────────────────────────────────────────────────────
    st.markdown("### 🩺 Health Check")
    health = run_health_check(config_path=cfg_path)
    overall = health["overall_status"]
    color   = STATUS_COLORS.get(overall, "#6b7280")

    h1, h2, h3, h4 = st.columns(4)
    h1.markdown(f'<div style="background:#0f1117;border:2px solid {color};border-radius:10px;padding:12px;text-align:center"><div style="font-size:11px;color:#9ca3af">Overall</div><div style="font-size:22px;font-weight:700;color:{color}">{overall}</div></div>', unsafe_allow_html=True)
    h2.metric("Pass",  health["summary"]["pass"])
    h3.metric("Warn",  health["summary"]["warn"])
    h4.metric("Fail",  health["summary"]["fail"])

    for check in health["checks"]:
        c = STATUS_COLORS.get(check["status"],"#6b7280")
        st.markdown(
            f'<div style="background:#0f1117;border:1px solid {c}44;border-radius:8px;'
            f'padding:10px;margin-bottom:6px;display:flex;justify-content:space-between">'
            f'<div><span style="font-size:13px;font-weight:600;color:#f9fafb">{check["name"]}</span>'
            f'<br><span style="font-size:11px;color:#9ca3af">{check["message"]}</span></div>'
            f'<span style="background:{c};color:#fff;padding:2px 10px;border-radius:20px;'
            f'font-size:11px;font-weight:700;height:fit-content">{check["status"]}</span></div>',
            unsafe_allow_html=True,
        )

    if health.get("recommendations"):
        with st.expander("💡 Recommendations"):
            for r in health["recommendations"]:
                st.caption(f"• {r}")

    # ── Bootstrap ────────────────────────────────────────────────────────────
    st.divider()
    st.markdown("### 🚀 Bootstrap Environment")
    st.caption("Idempotent — creates missing folders, seed CSVs, and state files. Never overwrites existing files.")

    if st.button("▶ Run Bootstrap", key="sys_bootstrap"):
        result = bootstrap_environment(config_path=cfg_path)
        created  = result["summary"]["created"]
        existing = result["summary"]["existing"]
        if created > 0:
            st.success(f"Bootstrap complete — created {created} files/dirs, found {existing} already present.")
        else:
            st.info(f"Environment already fully seeded — {existing} files/dirs verified.")
        with st.expander("Bootstrap details"):
            st.json(result, expanded=False)
        st.rerun()

    # ── Deployment Packet ─────────────────────────────────────────────────────
    st.divider()
    st.markdown("### 📦 Deployment Packet")
    st.caption("Bundles config, governance artifacts, runtime state, and analytics logs into a zip archive.")

    pkt_name    = st.text_input("Packet name", value="release_packet", key="sys_pkt_name")
    include_zip = st.checkbox("Create zip archive", value=True, key="sys_pkt_zip")
    full_logs   = st.checkbox("Include full governance logs", value=False, key="sys_pkt_full")

    if st.button("📦 Build Deployment Packet", key="sys_build_pkt"):
        from engines.deployment_packet import DeploymentPacketBuilder
        builder = DeploymentPacketBuilder(
            output_dir=pkt_dir, logs_dir="logs", state_dir="state",
            snapshots_dir="snapshots", config_path=cfg_path,
        )
        with st.spinner("Building packet..."):
            result = builder.build_packet(
                packet_name=pkt_name, include_zip=include_zip,
                include_full_logs=full_logs,
            )
        st.success(f"Packet built: `{result['packet_id']}`")
        if result.get("zip_path") and os.path.exists(result["zip_path"]):
            st.download_button(
                "⬇ Download Packet (.zip)",
                data=open(result["zip_path"],"rb").read(),
                file_name=f"{pkt_name}.zip", mime="application/zip",
                use_container_width=True,
            )
        with st.expander("Packet manifest"):
            st.json(result["deployment_manifest"], expanded=False)

    # ── Release Manifest ──────────────────────────────────────────────────────
    st.divider()
    st.markdown("### 📋 Release Manifest")

    from engines.release_manifest import ReleaseManifest
    manifest_path = "/tmp/options_ai_logs/release_manifest.csv" if os.path.exists("/mount/src") else "logs/release_manifest.csv"
    rm   = ReleaseManifest(path=manifest_path)
    rows = rm.list_releases(limit=20)

    if rows:
        import pandas as pd
        df = pd.DataFrame(rows)[["created_at","release_type","release_name","portfolio_run_id","health_status","notes"]].fillna("")
        st.dataframe(df, use_container_width=True, hide_index=True)
        labels = [f"{r['created_at'][:19]} · {r['release_type']} · {r['release_name']}" for r in rows]
        sel    = st.selectbox("Select release", range(len(labels)), format_func=lambda i: labels[i], key="sys_rel_sel")
        detail = rm.get_release(rows[sel]["release_id"])
        with st.expander("Release detail"):
            st.json(detail, expanded=False)
    else:
        st.caption("No releases yet — build a deployment packet or run the portfolio engine to create a release entry.")


# ─────────────────────────────────────────────
# LIVE DATA PANEL
# ─────────────────────────────────────────────

def _render_live_data_panel() -> None:
    """
    📡 Live Data tab — run the engine against real market data.

    Provider options:
      massive  — Polygon.io (Options Starter plan, key in MASSIVE_API_KEY)
      csv      — exported CSV files in data/reports/, data/chains/, data/positions/
      mock     — deterministic test data (always works, no API key needed)

    Broker position tracking (Tradier) connects here once approved.
    """
    import os
    from providers.provider_factory import build_provider
    from providers.runtime_data_service import RuntimeDataService

    st.markdown("### 📡 Live Data Runtime")
    st.caption("Select a provider, enter symbols, and run the full portfolio engine against real data.")

    # ── Provider selector ─────────────────────────────────────────────────────
    provider_options = ["mock", "massive", "csv"]
    provider_labels  = {
        "mock":    "🧪 Mock — deterministic test data (no API key)",
        "massive": "📈 Massive/Polygon — live options data (MASSIVE_API_KEY required)",
        "csv":     "📂 CSV — exported broker/chain files",
    }
    provider_type = st.radio(
        "Data Provider",
        options=provider_options,
        format_func=lambda p: provider_labels[p],
        horizontal=True,
        key="live_provider",
    )

    # ── Provider-specific config ──────────────────────────────────────────────
    provider_kwargs: dict = {}
    if provider_type == "massive":
        api_key = st.text_input(
            "MASSIVE_API_KEY",
            value=os.getenv("MASSIVE_API_KEY", ""),
            type="password",
            help="Set via environment variable or enter here. Never committed to git.",
            key="live_api_key",
        )
        if api_key:
            provider_kwargs["api_key"] = api_key

    elif provider_type == "csv":
        st.caption("Expected file layout: `data/reports/{SYM}_report.csv`, `data/chains/{SYM}_chain.csv`")
        provider_kwargs["reports_dir"]   = st.text_input("Reports dir",   "data/reports",  key="live_rdir")
        provider_kwargs["chains_dir"]    = st.text_input("Chains dir",    "data/chains",   key="live_cdir")
        provider_kwargs["positions_path"]= st.text_input("Positions file","data/positions/open_positions.csv", key="live_ppath")

    # ── Symbols + run options ─────────────────────────────────────────────────
    symbols_raw = st.text_input("Symbols (comma-separated)", value="SPY", key="live_symbols")
    symbols     = [s.strip().upper() for s in symbols_raw.split(",") if s.strip()]

    col1, col2, col3 = st.columns(3)
    log_events   = col1.checkbox("Log backtest events", key="live_log_ev")
    log_journal  = col2.checkbox("Log execution journal", key="live_log_ej")
    persist_st   = col3.checkbox("Persist state + snapshots", key="live_persist")

    # ── Status indicator ──────────────────────────────────────────────────────
    if provider_type == "massive":
        key_present = bool(provider_kwargs.get("api_key") or os.getenv("MASSIVE_API_KEY",""))
        if key_present:
            st.success("✅ MASSIVE_API_KEY detected — ready for live data")
        else:
            st.warning("⚠️ No MASSIVE_API_KEY — set it in Streamlit secrets or above")
    elif provider_type == "csv":
        rdir = provider_kwargs.get("reports_dir","data/reports")
        if os.path.isdir(rdir):
            csvs = [f for f in os.listdir(rdir) if f.endswith("_report.csv")]
            st.success(f"✅ Found {len(csvs)} report file(s) in {rdir}")
        else:
            st.warning(f"⚠️ Reports dir not found: {rdir} — create it with sample files to test")

    # ── Run button ────────────────────────────────────────────────────────────
    if not st.button("▶ Run Live Engine", type="primary", key="live_run"):
        # Show provider capability table when idle
        st.divider()
        st.markdown("**Provider capability comparison:**")
        cap_data = {
            "Capability": ["Spot price","Option chain","Greeks (Δ,Γ,θ,V)","IV / skew","ATR (live)","GEX (from chain OI)","IV percentile","Open positions","Fill prices"],
            "Mock":        ["✅","✅","✅","✅","✅","✅","✅","✅","—"],
            "Massive/Polygon":["✅","✅","✅","✅","✅ (v2/aggs)","✅","⚠️ est","—","—"],
            "CSV":         ["✅","✅","if provided","if provided","if provided","from OI","if provided","✅ file","—"],
            "Tradier (pending)":["✅","✅","✅","✅","—","from OI","—","✅ live","✅"],
        }
        import pandas as pd
        st.dataframe(pd.DataFrame(cap_data), use_container_width=True, hide_index=True)
        st.caption("⚠️ = approximate/estimated  |  — = not available from this source")
        return

    # ── Execute ───────────────────────────────────────────────────────────────
    try:
        provider = build_provider(provider_type, **provider_kwargs)
    except Exception as e:
        st.error(f"Failed to initialize provider: {e}")
        return

    svc = RuntimeDataService(provider)
    st.caption(f"Provider: `{svc.provider_name}` | Symbols: {symbols}")

    with st.spinner(f"Running engine via {svc.provider_name}..."):
        try:
            output = svc.run_portfolio(
                symbols,
                config_path="config/config.yaml",
                log_backtest_events=log_events,
                log_execution_journal=log_journal,
                persist_state=persist_st,
                snapshot_history=persist_st,
            )
        except Exception as e:
            st.error(f"Engine error: {e}")
            st.exception(e)
            return

    meta  = output["portfolio_meta"]
    alloc = output["allocation"]

    # Summary metrics
    m1,m2,m3,m4,m5,m6 = st.columns(6)
    m1.metric("Symbols",  meta["symbols_processed"])
    m2.metric("Ranked",   meta["total_ranked_trades"])
    m3.metric("Selected", meta["selected_trades"])
    m4.metric("Rejected", meta["rejected_trades"])
    m5.metric("Budget",   f"${alloc['total_risk_budget']:,.0f}")
    m6.metric("Used",     f"${alloc['used_risk_budget']:,.0f}")

    # ── Portfolio Harvest Panel (v26) ─────────────────────────────────────────
    _render_portfolio_harvest_panel(output)

    # Per-symbol results
    for sym_block in output["symbols"]:
        eng = sym_block["engine_output"]
        sym = sym_block["symbol"]
        vga = eng.get("vga","unknown")
        n   = len(eng.get("candidates",[]))

        VGA_COLORS = {"premium_selling":"#22c55e","neutral_time_spreads":"#3b82f6",
                      "cautious_directional":"#f59e0b","trend_directional":"#ef4444","mixed":"#6b7280"}
        col = VGA_COLORS.get(vga,"#6b7280")

        st.markdown(
            f'<div style="background:#0f1117;border:1px solid {col}44;border-radius:10px;'
            f'padding:12px;margin-bottom:8px">'
            f'<div style="display:flex;justify-content:space-between">'
            f'<div><span style="font-size:16px;font-weight:700;color:#f9fafb">{sym}</span>'
            f'<span style="margin-left:12px;font-size:11px;color:#9ca3af">via {svc.provider_name}</span></div>'
            f'<span style="background:{col};color:#fff;padding:3px 12px;border-radius:20px;'
            f'font-size:11px;font-weight:700">{vga.replace("_"," ").upper()}</span></div>'
            f'<div style="font-size:12px;color:#9ca3af;margin-top:6px">'
            f'spot ${eng["market"].get("spot_price",0):.2f} | '
            f'EM ±${eng["derived"].get("expected_move",0):.2f} | '
            f'candidates: {n}</div></div>',
            unsafe_allow_html=True,
        )

        for c in eng.get("candidates",[])[:3]:
            st_type = c.get("strategy_type","").replace("_"," ").title()
            score   = c.get("confidence_score",0)
            dec     = c.get("decision","")
            dec_col = {"STRONG":"#22c55e","TRADABLE":"#3b82f6","SKIP":"#6b7280"}.get(dec,"#6b7280")
            st.markdown(
                f'&nbsp;&nbsp;&nbsp;'
                f'<span style="color:{dec_col};font-weight:700">●</span> '
                f'`{st_type}` score={score:.0f} '
                f'<span style="color:{dec_col};font-size:11px">{dec}</span>',
                unsafe_allow_html=True,
            )

    # Alerts
    high_alerts = [a for a in output.get("alerts",[]) if a.get("severity") in ("HIGH","CRITICAL")]
    if high_alerts:
        st.divider()
        st.markdown("#### 🔴 High Priority Alerts")
        for a in high_alerts[:5]:
            st.error(f"**{a['title']}** — {a['message']}")

    # Selected trades
    selected = alloc.get("selected_trades",[])
    if selected:
        st.divider()
        st.markdown("#### ✅ Selected Trades")
        for t in selected:
            st.markdown(
                f"**{t.get('symbol','')} {str(t.get('strategy_type',t.get('strategy',''))).replace('_',' ').title()}** "
                f"score={t.get('confidence_score',t.get('score',0)):.0f} | "
                f"risk=${t.get('_risk',0):.0f} | "
                f"contracts={t.get('contracts',1)}"
            )

    with st.expander(f"Raw output — {meta['run_id'][:30]}"):
        st.json(meta)


# ─────────────────────────────────────────────
# CALENDAR/DIAGONAL LIFECYCLE PANEL
# ─────────────────────────────────────────────

def _render_lifecycle_signals(snapshot: dict) -> None:
    """
    Renders calendar/diagonal lifecycle signals from the position monitor.
    Called from within the Positions tab when lifecycle data is present.
    """
    lifecycle = snapshot.get("calendar_diagonal_lifecycle", [])
    if not lifecycle:
        return

    st.divider()
    st.markdown("### 📅 Calendar / Diagonal Lifecycle")

    ACTION_COLORS = {
        "HOLD":                 "#374151",
        "ROLL_SHORT":           "#7c3aed",
        "ROLL_DIAGONAL_SHORT":  "#7c3aed",
        "CONVERT_TO_DIAGONAL":  "#16a34a",
        "EXIT_LONG_WINDOW":     "#dc2626",
        "EXIT_STRUCTURE_BREAK": "#dc2626",
        "EXIT_ENVIRONMENT":     "#dc2626",
        "ENTER_CALENDAR":       "#2563eb",
    }
    URGENCY_COLORS = {"HIGH": "#dc2626", "MEDIUM": "#f59e0b", "LOW": "#6b7280"}

    for sig in lifecycle:
        action  = sig.get("action", "HOLD")
        urgency = sig.get("urgency", "LOW")
        sym     = sig.get("symbol", "—")
        struct  = sig.get("structure_type", "calendar")
        acolor  = ACTION_COLORS.get(action, "#374151")
        ucolor  = URGENCY_COLORS.get(urgency, "#6b7280")
        dec     = sig.get("decision", {})

        st.markdown(
            f'<div style="background:#0f1117;border:1px solid {acolor}66;'
            f'border-radius:10px;padding:12px;margin-bottom:8px">'
            f'<div style="display:flex;justify-content:space-between;align-items:center">'
            f'<div><span style="font-size:14px;font-weight:700;color:#f9fafb">'
            f'{sym} {struct.title()}</span>'
            f'<span style="margin-left:8px;font-size:11px;color:#9ca3af">'
            f'long ${sig.get("long_strike",0):.0f} / short ${sig.get("short_strike",0):.0f} | '
            f'long {sig.get("long_dte",0)} DTE / short {sig.get("short_dte",0)} DTE</span></div>'
            f'<div style="display:flex;gap:8px">'
            f'<span style="background:{ucolor};color:#fff;padding:2px 10px;'
            f'border-radius:20px;font-size:10px;font-weight:700">{urgency}</span>'
            f'<span style="background:{acolor};color:#fff;padding:2px 10px;'
            f'border-radius:20px;font-size:10px;font-weight:700">{action.replace("_"," ")}</span>'
            f'</div></div>'
            f'<div style="font-size:11px;color:#9ca3af;margin-top:6px">'
            f'{dec.get("rationale","")}</div>'
            f'{"<div style=font-size:11px;color:#6b7280;margin-top:4px>" + dec.get("notes","") + "</div>" if dec.get("notes") else ""}'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Show target strikes for actionable decisions
        if action not in ("HOLD", "NO_ACTION") and dec.get("target_short_strike"):
            cols = st.columns(4)
            cols[0].metric("Target Short", f'${dec["target_short_strike"]:.0f}')
            if dec.get("target_long_strike"):
                cols[1].metric("Target Long",  f'${dec["target_long_strike"]:.0f}')
            if dec.get("target_short_dte"):
                cols[2].metric("Target S-DTE", dec["target_short_dte"])
            if dec.get("target_long_dte"):
                cols[3].metric("Target L-DTE", dec["target_long_dte"])


# ─────────────────────────────────────────────
# HARVEST VIEW — positions tab upgrade
# ─────────────────────────────────────────────

def _harvest_badge_html(badge: str) -> str:
    """Render a colored harvest badge pill."""
    colors = {
        "GOLD":   ("#f59e0b", "#000"),
        "GREEN":  ("#22c55e", "#fff"),
        "RED":    ("#ef4444", "#fff"),
        "BLUE":   ("#3b82f6", "#fff"),
        "PURPLE": ("#7c3aed", "#fff"),
        "WAIT":   ("#6b7280", "#fff"),
        "—":      ("#1f2937", "#6b7280"),
    }
    bg, fg = colors.get(badge, ("#1f2937", "#6b7280"))
    return (f'<span style="background:{bg};color:{fg};padding:2px 10px;'
            f'border-radius:20px;font-size:11px;font-weight:700;'
            f'border:1px solid {bg}">{badge}</span>')


def _render_harvest_row(pos: dict, market: dict, derived: dict) -> None:
    """Render a single position as a Harvest view card with bot action."""
    badge        = pos.get("harvest_badge", "—")
    net_liq      = pos.get("net_liq")
    harvestable  = pos.get("harvestable_equity")
    roll_credit  = pos.get("proposed_roll_credit")
    trap_dist    = pos.get("gamma_trap_distance")
    sentiment    = pos.get("sentiment_score", 0.0)
    flip_rec     = pos.get("flip_recommendation", "HOLD_STRUCTURE")
    bot_action   = pos.get("bot_action", "HOLD")
    bot_priority = pos.get("bot_priority", 6)
    bot_rationale= pos.get("bot_rationale", "")
    contracts_add= pos.get("recommended_contract_add", 0)
    sym          = pos.get("symbol", "")
    struct       = pos.get("strategy_type", "").replace("_", " ").title()
    action       = (pos.get("decision", {}).get("action")
                    or pos.get("management_status", bot_action))

    border_color = {
        "GOLD":   "#f59e0b",
        "GREEN":  "#22c55e",
        "RED":    "#ef4444",
        "BLUE":   "#3b82f6",
        "PURPLE": "#7c3aed",
    }.get(badge, "#374151")

    st.markdown(
        f'<div style="background:#0f1117;border:1px solid {border_color}66;'
        f'border-radius:10px;padding:12px;margin-bottom:8px">'
        f'<div style="display:flex;justify-content:space-between;align-items:center">'
        f'<div><span style="font-size:15px;font-weight:700;color:#f9fafb">{sym} {struct}</span>'
        f'&nbsp;&nbsp;<span style="font-size:11px;color:#9ca3af">{action.replace("_"," ")}</span></div>'
        f'{_harvest_badge_html(badge)}</div>'
        f'<div style="display:grid;grid-template-columns:repeat(7,1fr);gap:8px;margin-top:10px">'
        f'<div><div style="font-size:9px;color:#6b7280">Net Liq</div>'
        f'<div style="font-size:13px;color:#e5e7eb">'
        f'{"${:+.0f}".format(net_liq) if net_liq is not None else "—"}</div></div>'
        f'<div><div style="font-size:9px;color:#6b7280">Harvestable</div>'
        f'<div style="font-size:13px;color:#e5e7eb">'
        f'{"${:.2f}".format(harvestable) if harvestable is not None else "—"}</div></div>'
        f'<div><div style="font-size:9px;color:#6b7280">Roll Credit</div>'
        f'<div style="font-size:13px;color:{"#f59e0b" if (roll_credit or 0) >= 5 else "#22c55e" if (roll_credit or 0) >= 1 else "#6b7280"}">'
        f'{"${:.2f}".format(roll_credit) if roll_credit is not None else "—"}</div></div>'
        f'<div><div style="font-size:9px;color:#6b7280">Badge</div>'
        f'{_harvest_badge_html(badge)}</div>'
        f'<div><div style="font-size:9px;color:#6b7280">Trap Dist</div>'
        f'<div style="font-size:13px;color:{"#ef4444" if (trap_dist or 1) < 0.02 else "#e5e7eb"}">'
        f'{"  {:.1%}".format(trap_dist) if trap_dist is not None else "—"}</div></div>'
        f'<div><div style="font-size:9px;color:#6b7280">Sentiment</div>'
        f'<div style="font-size:13px;color:{"#22c55e" if sentiment > 0.35 else "#ef4444" if sentiment < -0.35 else "#e5e7eb"}">'
        f'{sentiment:+.2f}</div></div>'
        f'<div><div style="font-size:9px;color:#6b7280">Flip Rec</div>'
        f'<div style="font-size:10px;color:#9ca3af">'
        f'{flip_rec.replace("_"," ").replace("HOLD STRUCTURE","—")}</div></div>'
        f'</div>'
        # Bot action row
        f'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:8px;padding-top:8px;border-top:1px solid #1f2937">'
        f'<div><div style="font-size:9px;color:#6b7280">Bot Action</div>'
        f'<div style="font-size:12px;font-weight:700;color:{{"EXIT_NOW":"#ef4444","DE_RISK":"#f97316","HARVEST_NOW":"#f59e0b","FLIP_NOW":"#7c3aed","ROLL_NOW":"#22c55e","SCALE_IN":"#3b82f6","HOLD":"#6b7280"}}.get(bot_action,"#6b7280")'
        f'">{bot_action.replace("_"," ")}</div></div>'
        f'<div><div style="font-size:9px;color:#6b7280">Priority</div>'
        f'<div style="font-size:12px;color:#e5e7eb">P{bot_priority}</div></div>'
        f'<div><div style="font-size:9px;color:#6b7280">Add Contracts</div>'
        f'<div style="font-size:12px;color:{"#3b82f6" if contracts_add > 0 else "#6b7280"}">'
        f'{"+" + str(contracts_add) if contracts_add > 0 else "—"}</div></div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )
    if bot_rationale:
        st.caption(f"🤖 {bot_rationale}")

    # Action buttons
    bc1, bc2, bc3 = st.columns(3)
    with bc1:
        if st.button("🔍 Ask Analyst", key=f"analyst_{sym}_{pos.get('short_strike',0)}",
                     use_container_width=True):
            from agents.analyst_bridge import get_analyst_brief
            mctx = {
                "spot_price":    market.get("spot_price"),
                "gamma_regime":  derived.get("gamma_regime",""),
                "iv_regime":     derived.get("iv_regime",""),
                "vga_environment": derived.get("vga_environment",""),
                "gamma_trap":    derived.get("gamma_trap"),
                "put_25d_iv":    derived.get("put_25d_iv"),
                "call_25d_iv":   derived.get("call_25d_iv"),
                "expected_move": derived.get("expected_move"),
            }
            with st.spinner("Generating analysis..."):
                result = get_analyst_brief(pos, mctx, use_llm=False)
            brief = result["brief"]
            st.info(f"**Diagnosis:** {brief['diagnosis']}")
            st.success(f"**Harvest Move:** {brief['harvest_move']}")
            st.warning(f"**Risk Warning:** {brief['risk_warning']}")

    with bc2:
        if st.button("📋 Draft Roll Ticket", key=f"ticket_{sym}_{pos.get('short_strike',0)}",
                     use_container_width=True):
            from execution.execution_engine import draft_roll_ticket
            harvest_summary = pos.get("harvest_summary", {})
            ticket_result   = draft_roll_ticket(pos, harvest_summary)
            if ticket_result["status"] == "READY":
                st.json(ticket_result["ticket"])
            else:
                st.warning(ticket_result["reason"])

    with bc3:
        flip_cand = pos.get("flip_candidate") or (flip_rec not in ("HOLD_STRUCTURE",""))
        if flip_cand:
            if st.button("🔄 Preview Flip", key=f"flip_{sym}_{pos.get('short_strike',0)}",
                         use_container_width=True):
                from dashboard.flip_preview import render_flip_preview
                with st.container():
                    render_flip_preview(pos)

    # Transition preview — only for calendars/diagonals with approved transition
    if pos.get("transition_is_credit_approved") and pos.get("transition_action") != "HOLD_CURRENT_HARVEST":
        trans_color = {
            "FLIP_TO_CALL_DIAGONAL":      "#1d4ed8",
            "FLIP_TO_PUT_DIAGONAL":       "#dc2626",
            "CONVERT_TO_BULL_PUT_SPREAD": "#16a34a",
            "CONVERT_TO_BEAR_CALL_SPREAD":"#f97316",
        }.get(pos.get("transition_action",""), "#6b7280")
        st.markdown(
            f'<div style="margin:6px 0;padding:6px 12px;border-left:4px solid {trans_color};'
            f'background:#0f1117;border-radius:6px">'
            f'<strong style="color:{trans_color}">'
            f'{pos.get("transition_action","").replace("_"," ")}</strong> · '
            f'Credit ${pos.get("transition_net_credit",0):.2f}/share · '
            f'Roll score {pos.get("transition_future_roll_score",0):.0f}</div>',
            unsafe_allow_html=True,
        )
        with st.expander("🔄 Preview Transition", expanded=False):
            from dashboard.transition_preview import render_transition_preview, render_transition_orders
            from execution.transition_ticket_builder import build_transition_ticket
            render_transition_preview(pos)
            ticket = build_transition_ticket(pos, {
                "recommended_action": pos.get("transition_action"),
                "transition_net_credit": pos.get("transition_net_credit",0),
                "why": pos.get("transition_why",[]),
                "new_structure": {
                    "type":      pos.get("transition_new_structure_type",""),
                    "long_leg":  pos.get("transition_new_long_leg"),
                    "short_leg": pos.get("transition_new_short_leg"),
                },
            })
            st.divider()
            render_transition_orders(pos, ticket)

    # Update marks — inline expander under each position card
    with st.expander(f"✏️ Update marks for {sym}", expanded=False):
        _render_update_marks_form(pos)


def _render_harvest_view(snapshot: dict, market: dict, derived: dict) -> None:
    """
    Upgraded Positions tab: Harvest view with summary cards + per-position rows.
    """
    all_positions = (snapshot.get("calendar_diagonal", [])
                     + snapshot.get("credit_spreads", [])
                     + snapshot.get("debit_spreads", []))

    # ── Summary cards ─────────────────────────────────────────────────────────
    total        = len(all_positions)
    gold_count   = sum(1 for p in all_positions if p.get("harvest_badge") == "GOLD")
    green_count  = sum(1 for p in all_positions if p.get("harvest_badge") == "GREEN")
    red_count    = sum(1 for p in all_positions if p.get("harvest_badge") == "RED")
    blue_count   = sum(1 for p in all_positions if p.get("harvest_badge") == "BLUE")
    total_harv   = sum(p.get("harvestable_equity", 0) or 0 for p in all_positions)
    assign_risk  = sum(1 for p in all_positions if p.get("harvest_summary", {}).get("assignment_risk"))

    c1,c2,c3,c4,c5,c6,c7 = st.columns(7)
    c1.metric("Total",      total)
    c2.metric("🥇 Gold",   gold_count)
    c3.metric("🟢 Green",  green_count)
    c4.metric("🔴 Risk",   red_count)
    c5.metric("🔵 Flip",   blue_count)
    c6.metric("⚠️ Assign", assign_risk)
    c7.metric("Harvestable", f"${total_harv:,.0f}")

    if not all_positions:
        return

    st.divider()

    # Sort: RED first, then GOLD, GREEN, BLUE, WAIT, —
    badge_order = {"RED":0,"GOLD":1,"GREEN":2,"BLUE":3,"WAIT":4,"—":5}
    sorted_pos  = sorted(all_positions, key=lambda p: badge_order.get(p.get("harvest_badge","—"), 5))

    for pos in sorted_pos:
        _render_harvest_row(pos, market, derived)


# ─────────────────────────────────────────────
# PORTFOLIO HARVEST PANEL (v26)
# ─────────────────────────────────────────────

def _render_portfolio_harvest_panel(portfolio_output: dict) -> None:
    """
    Summary cards for the Portfolio tab: harvestable equity, gold/risk/flip counts.
    Collects VH fields from all open positions across all symbol engine outputs.
    """
    all_positions = []
    for sym_block in portfolio_output.get("symbols", []):
        eng = sym_block.get("engine_output", {})
        pos = eng.get("positions", {})
        for bucket in ("calendar_diagonal", "credit_spreads", "debit_spreads"):
            all_positions.extend(pos.get(bucket, []))

    if not all_positions:
        return

    total_harv   = sum(p.get("harvestable_equity", 0) or 0 for p in all_positions)
    gold_count   = sum(1 for p in all_positions if p.get("harvest_badge") == "GOLD")
    green_count  = sum(1 for p in all_positions if p.get("harvest_badge") == "GREEN")
    red_count    = sum(1 for p in all_positions if p.get("harvest_badge") == "RED")
    flip_count   = sum(1 for p in all_positions if p.get("flip_recommendation","HOLD_STRUCTURE") != "HOLD_STRUCTURE")
    assign_count = sum(1 for p in all_positions if (p.get("harvest_summary") or {}).get("assignment_risk"))
    # Bot action counts
    harvest_ct   = sum(1 for p in all_positions if p.get("bot_action") in ("HARVEST_NOW","ROLL_NOW"))
    scale_ct     = sum(1 for p in all_positions if p.get("bot_action") == "SCALE_IN")
    derisk_ct    = sum(1 for p in all_positions if p.get("bot_action") in ("DE_RISK","EXIT_NOW"))
    total_add    = sum(p.get("recommended_contract_add", 0) or 0 for p in all_positions)

    st.divider()
    st.markdown("#### 🌾 Portfolio Harvest Summary")
    h1,h2,h3,h4,h5,h6 = st.columns(6)
    h1.metric("Harvestable",   f"${total_harv:,.0f}")
    h2.metric("🥇 Harvest Now", harvest_ct)
    h3.metric("🔵 Scale Ready", scale_ct)
    h4.metric("🔴 De-Risk",    derisk_ct)
    h5.metric("🔵 Flip Ready", flip_count)
    h6.metric("⚠️ Assign Risk", assign_count)
    if total_add > 0 or gold_count > 0:
        s1,s2,s3 = st.columns(3)
        s1.metric("Gold Harvests",    gold_count)
        s2.metric("Contracts to Add", f"+{total_add}")
        s3.metric("Green + Purple",   green_count + sum(1 for p in all_positions if p.get("harvest_badge")=="PURPLE"))

    # Top 3 roll opportunities
    rollable = sorted(
        [p for p in all_positions if (p.get("proposed_roll_credit") or 0) > 0],
        key=lambda p: p.get("proposed_roll_credit", 0), reverse=True
    )[:3]
    if rollable:
        st.markdown("**Top roll opportunities:**")
        for p in rollable:
            badge = p.get("harvest_badge", "—")
            sym   = p.get("symbol", "")
            strat = p.get("strategy_type", "").replace("_"," ").title()
            cred  = p.get("proposed_roll_credit", 0)
            flip  = p.get("flip_recommendation", "HOLD_STRUCTURE").replace("_"," ")
            st.markdown(
                f'&nbsp;&nbsp;{_harvest_badge_html(badge)} '
                f'`{sym} {strat}` — roll credit **${cred:.2f}** | flip: {flip}',
                unsafe_allow_html=True,
            )


# ─────────────────────────────────────────────
# TRADE ENTRY FORM
# ─────────────────────────────────────────────

def _render_trade_entry_form(logger) -> None:
    """
    ➕ Enter Trade — manual position entry form.

    Writes directly to trade_log.csv so the position tracker,
    harvest engine, flip optimizer, and bot pipeline can work on it.

    Works for trades opened in any broker (ThinkorSwim, Schwab, IBKR, etc.)
    without any API connection.
    """
    import os
    from datetime import date, datetime

    st.markdown("### ➕ Log a Trade from ThinkorSwim / Schwab")
    st.caption(
        "Enter any open options position here. "
        "Once logged, it appears in the Positions tab with harvest signals, "
        "flip recommendations, and bot action."
    )

    # ── Strategy selector ─────────────────────────────────────────────────────
    STRATEGY_OPTIONS = {
        "calendar":        "📅 Calendar (same strike, different expiry)",
        "diagonal":        "↗ Diagonal (different strike + expiry)",
        "bull_put":        "🟢 Bull Put Credit Spread",
        "bear_call":       "🔴 Bear Call Credit Spread",
        "bull_call_debit": "↑ Bull Call Debit Spread",
        "bear_put_debit":  "↓ Bear Put Debit Spread",
        "double_diagonal": "⇔ Double Diagonal",
    }

    with st.form("trade_entry_form", clear_on_submit=True):
        st.markdown("**Position details**")

        r1c1, r1c2, r1c3 = st.columns(3)
        symbol        = r1c1.text_input("Symbol", value="", placeholder="e.g. TSLA").upper().strip()
        strategy_key  = r1c2.selectbox("Strategy", list(STRATEGY_OPTIONS.keys()),
                                        format_func=lambda k: STRATEGY_OPTIONS[k])
        option_side   = r1c3.selectbox("Option type", ["call","put"])

        st.markdown("**Strikes & expirations**")
        r2c1, r2c2, r2c3, r2c4 = st.columns(4)
        short_strike = r2c1.number_input("Short strike $", min_value=0.0, value=0.0,
                                          step=1.0, format="%.1f",
                                          help="e.g. 350 for TSLA $350 strike")
        long_strike  = r2c2.number_input("Long strike $",  min_value=0.0, value=0.0,
                                          step=1.0, format="%.1f",
                                          help="Same as short for calendars. Different for diagonals.")
        short_expiration  = r2c3.date_input("Short expiry",  value=date.today())
        long_expiration   = r2c4.date_input("Long expiry",   value=date.today())

        st.markdown("**Entry economics**")
        r3c1, r3c2, r3c3, r3c4 = st.columns(4)
        entry_price = r3c1.number_input(
            "Entry debit / credit $",
            min_value=-500.0, max_value=500.0, value=0.0, step=0.05, format="%.2f",
            help="Debit = positive (you paid to open). Credit = negative (you received).",
        )
        contracts  = r3c2.number_input("Contracts", min_value=1, max_value=100, value=1, step=1)
        spot_open  = r3c3.number_input("Spot price at entry $", min_value=0.0, step=0.01, format="%.2f")
        date_open  = r3c4.date_input("Date opened", value=date.today())

        st.markdown("**Optional fields** (improve harvest + flip signals)")
        r4c1, r4c2, r4c3, r4c4 = st.columns(4)
        short_delta = r4c1.number_input("Short delta",  min_value=-1.0, max_value=1.0, step=0.01, format="%.2f")
        long_delta  = r4c2.number_input("Long delta",   min_value=-1.0, max_value=1.0, step=0.01, format="%.2f")
        entry_iv    = r4c3.number_input("Entry IV (e.g. 0.45)", min_value=0.0, max_value=5.0, step=0.01, format="%.3f")
        score       = r4c4.number_input("Score (0–100)", min_value=0, max_value=100, value=0, step=1)

        r5c1, r5c2 = st.columns(2)
        tether_id  = r5c1.text_input("Tether ID (optional)", placeholder="e.g. TSLA_CAL_001",
                                      help="Links legs together for harvest tracking.")
        notes      = r5c2.text_input("Notes", placeholder="e.g. ATM calendar, earnings play")

        submitted = st.form_submit_button("💾 Log Trade", type="primary", use_container_width=True)

    if not submitted:
        return

    # ── Validation ────────────────────────────────────────────────────────────
    errors = []
    if not symbol:
        errors.append("Symbol is required.")
    if short_strike <= 0 and long_strike <= 0:
        errors.append("At least one strike must be > 0.")
    if short_expiration > long_expiration and strategy_key in ("calendar","diagonal","double_diagonal"):
        errors.append("Long expiry must be on or after short expiry for multi-leg structures.")
    if errors:
        for e in errors:
            st.error(e)
        return

    # ── Build trade row ───────────────────────────────────────────────────────
    from backtest.trade_logger import _generate_id
    trade_id   = _generate_id("M")   # "M" prefix = manually entered

    # Compute DTEs
    today = date.today()
    short_dte_val = max((short_expiration - today).days, 0)
    long_dte_val  = max((long_expiration  - today).days, 0)

    # Estimate max loss for credit spreads
    spread_width = abs(short_strike - long_strike) * 100 * contracts
    max_loss_est = (
        max(spread_width - abs(entry_price) * 100 * contracts, 0.0)
        if strategy_key in ("bull_put","bear_call") else
        abs(entry_price) * 100 * contracts
    )

    candidate = {
        "trade_id":         trade_id,
        "symbol":           symbol,
        "strategy_type":    strategy_key,
        "direction":        f"{option_side}_{strategy_key}",
        "option_side":      option_side,
        "short_strike":     short_strike if short_strike > 0 else None,
        "long_strike":      long_strike  if long_strike  > 0 else None,
        "short_expiration": short_expiration.isoformat(),
        "long_expiration":  long_expiration.isoformat(),
        "short_dte":        short_dte_val,
        "long_dte":         long_dte_val,
        "contracts":        contracts,
        "entry_debit_credit": entry_price,
        "entry_price":      abs(entry_price),
        "max_loss":         max_loss_est,
        "target_exit_value":round(abs(entry_price) * 1.20, 4),
        "stop_value":       round(abs(entry_price) * 0.75, 4),
        "short_delta":      short_delta if short_delta != 0 else None,
        "long_delta":       long_delta  if long_delta  != 0 else None,
        "confidence_score": score if score > 0 else None,
        "notes":            f"tether:{tether_id} | {notes}".strip(" |") if tether_id else notes,
    }
    market_ctx = {
        "symbol":    symbol,
        "spot_price": spot_open,
    }
    derived_ctx = {}
    if entry_iv > 0:
        derived_ctx["iv_regime"] = (
            "elevated" if entry_iv > 0.30 else
            "moderate" if entry_iv > 0.20 else "low"
        )

    try:
        trade_id_returned = logger.open_trade(candidate, market_ctx, derived_ctx,
                                               notes=candidate["notes"])
        st.success(f"✅ Trade logged: `{trade_id_returned}`")
        st.caption(
            f"**{symbol}** {STRATEGY_OPTIONS[strategy_key]} | "
            f"${short_strike} / ${long_strike} | "
            f"{short_expiration} / {long_expiration} | "
            f"{contracts} contract(s) | entry ${entry_price:+.2f}"
        )
        st.info(
            "👉 Switch to **📍 Positions** tab to see harvest signals, "
            "flip recommendations, and bot action for this trade."
        )
    except Exception as e:
        st.error(f"Failed to log trade: {e}")
        st.exception(e)


# ─────────────────────────────────────────────
# UPDATE MARKS FORM
# ─────────────────────────────────────────────

def _render_update_marks_form(pos: dict) -> None:
    """
    Inline form to update current mark prices for a logged position.
    Allows harvest math to produce real numbers without a live API.

    Reads current values from ThinkorSwim / Schwab Position tab:
      Mark column = current mid price per leg
    """
    import os
    from pathlib import Path
    from backtest.trade_logger import TradeLogger

    if os.path.exists("/mount/src"):
        log_dir = Path("/tmp/options_ai_logs")
    else:
        log_dir = Path(__file__).parent.parent / "logs"

    logger   = TradeLogger(log_dir=log_dir)
    trade_id = pos.get("trade_id", "")
    sym      = pos.get("symbol", "")

    st.caption(
        f"Enter current marks from your broker's Position tab. "
        f"Trade ID: `{trade_id}`"
    )

    # Show what's currently stored
    cur_long  = pos.get("current_long_mid")  or pos.get("current_value")
    cur_short = pos.get("current_short_mid") or pos.get("mark")

    col1, col2, col3, col4 = st.columns(4)
    new_long  = col1.number_input(
        "Long leg mark $",
        min_value=0.0, value=float(cur_long or 0.0),
        step=0.05, format="%.2f",
        key=f"upd_long_{trade_id}",
        help=f"Current mid price of the long leg from ThinkorSwim Mark column",
    )
    new_short = col2.number_input(
        "Short leg mark $",
        min_value=0.0, value=float(cur_short or 0.0),
        step=0.05, format="%.2f",
        key=f"upd_short_{trade_id}",
        help=f"Current mid price of the short leg (use positive value)",
    )
    new_spot = col3.number_input(
        "Current spot $",
        min_value=0.0, value=float(pos.get("live_spot") or 0.0),
        step=0.5, format="%.2f",
        key=f"upd_spot_{trade_id}",
        help=f"Current {sym} stock price",
    )
    new_delta = col4.number_input(
        "Short delta",
        min_value=0.0, max_value=1.0, value=float(abs(float(pos.get("short_delta") or 0))),
        step=0.01, format="%.2f",
        key=f"upd_delta_{trade_id}",
        help="Abs value of short leg delta (from ThinkorSwim Greeks tab)",
    )

    if st.button("💾 Save Marks", key=f"save_marks_{trade_id}", type="primary"):
        if not trade_id:
            st.warning("Cannot update — no trade_id on this position. Check trade_log.csv.")
            return
        try:
            updates = {}
            if new_long  > 0: updates["current_value"]   = new_long
            if new_short > 0: updates["mark"]             = new_short
            if new_spot  > 0: updates["spot_open"]        = new_spot
            if new_delta > 0: updates["short_delta"]      = new_delta

            # Also compute and store spread value + roll credit estimate
            if new_long > 0 and new_short > 0:
                import math
                spread = new_long - new_short
                updates["current_spread_value"] = round(spread, 4)
                short_dte = max(int(float(pos.get("short_dte") or 7)), 1)
                new_short_est = new_short * math.sqrt(7 / short_dte)
                roll_credit   = max(round(new_short_est - new_short, 4), 0.0)
                updates["proposed_roll_credit"] = roll_credit

            logger.update_trade(trade_id, updates)
            st.success(
                f"✅ Marks updated. "
                f"Spread value: ${new_long - new_short:.2f} | "
                f"Roll credit est: ${updates.get('proposed_roll_credit', 0):.2f}"
            )
            st.rerun()
        except Exception as e:
            st.error(f"Update failed: {e}")
            st.exception(e)


# ─────────────────────────────────────────────
# CLOSE TRADE FORM (unified update + close)
# ─────────────────────────────────────────────

def _render_close_trade_form(trade: dict, logger) -> None:
    """
    Unified form under each open position:
      - Update current marks (for harvest signals)
      - Close the trade (records exit price + P&L)

    Values to enter from ThinkorSwim / Schwab Positions tab:
      Mark column   → long leg mark / short leg mark
      P/L Open $    → realized P&L
    """
    import math
    trade_id = trade.get("trade_id", "")
    sym      = trade.get("symbol", "")
    entry_px = abs(float(trade.get("entry_price") or 0))
    contracts = max(1, int(float(trade.get("contracts") or 1)))

    st.caption(f"Trade: `{trade_id}` | {sym} {trade.get('strategy_type','')} | Entry ${entry_px:.2f}")

    # ── Update marks ─────────────────────────────────────────────────────────
    st.markdown("**Update current marks** *(from ThinkorSwim Mark column)*")
    m1, m2, m3, m4 = st.columns(4)

    cur_long  = float(trade.get("current_long_mid")  or trade.get("current_value") or 0)
    cur_short = float(trade.get("current_short_mid") or trade.get("mark") or 0)
    cur_spot  = float(trade.get("live_spot") or trade.get("spot_open") or 0)
    cur_delta = abs(float(trade.get("short_delta") or 0))

    new_long  = m1.number_input("Long leg mark $",  min_value=0.0, max_value=500.0,
                                 value=cur_long, step=0.05, format="%.2f", key=f"cl_long_{trade_id}",
                                 help="Option price of your long leg — e.g. 24.87, NOT the strike (350)")
    new_short = m2.number_input("Short leg mark $", min_value=0.0, max_value=500.0,
                                 value=cur_short, step=0.05, format="%.2f", key=f"cl_short_{trade_id}",
                                 help="Option price of your short leg — e.g. 24.05, NOT the strike (350)")
    new_spot  = m3.number_input("Spot $",           min_value=0.0, value=cur_spot,
                                 step=0.5,  format="%.2f", key=f"cl_spot_{trade_id}",
                                 help="Current stock price — e.g. 367.96 for TSLA")
    new_delta = m4.number_input("Short delta",      min_value=0.0, max_value=1.0, value=cur_delta,
                                 step=0.01, format="%.2f", key=f"cl_delta_{trade_id}",
                                 help="Abs value of short leg delta — 0.98 for deep ITM")

    # Sanity warning if mark looks like a strike price
    _spot_check = new_spot or cur_spot or 100.0
    if new_long >= _spot_check or new_short >= _spot_check:
        st.warning(
            f"⚠️ Long mark ${new_long:.2f} or short mark ${new_short:.2f} looks like a strike price, "
            f"not an option price. In ThinkorSwim, use the **Mark** column (e.g. $24.87), "
            f"not the strike (e.g. $350)."
        )

    if st.button("💾 Save Marks", key=f"save_m_{trade_id}"):
        updates = {}
        if new_long  > 0:
            updates["current_long_mid"] = new_long
            updates["current_value"]    = new_long
        if new_short > 0:
            updates["current_short_mid"] = new_short
            updates["mark"]              = new_short
        if new_spot  > 0: updates["live_spot"]   = new_spot
        if new_delta > 0: updates["short_delta"] = new_delta

        if new_long > 0 and new_short > 0:
            spread = round(new_long - new_short, 4)
            updates["current_spread_value"] = spread
            # Estimate roll credit: time-scaled new short vs buyback
            short_dte = max(int(float(trade.get("short_dte") or 7)), 1)
            new_short_est = new_short * math.sqrt(max(7, short_dte) / short_dte)
            roll_credit   = round(max(new_short_est - new_short, 0.0), 4)
            updates["proposed_roll_credit"] = roll_credit
            # P&L estimate
            pnl_est = round((spread - entry_px) * 100 * contracts, 2)
            st.info(
                f"Spread: ${spread:.2f} | Entry: ${entry_px:.2f} | "
                f"Est P&L: ${pnl_est:+.0f} | "
                f"Roll credit est: ${roll_credit:.2f}"
            )

        if updates:
            logger.update_trade(trade_id, updates)
            st.success("Marks saved.")
            st.rerun()

    st.divider()

    # ── Close trade ───────────────────────────────────────────────────────────
    st.markdown("**Close this trade** *(mark as exited)*")
    cl1, cl2, cl3 = st.columns(3)

    exit_spread = cl1.number_input(
        "Exit spread value $",
        min_value=0.0,
        value=float(trade.get("current_spread_value") or 0),
        step=0.05, format="%.2f",
        key=f"exit_px_{trade_id}",
        help="Current spread value (long mark − short mark) at time of close",
    )
    pnl_input = cl2.number_input(
        "P&L $ (from broker)",
        value=round((exit_spread - entry_px) * 100 * contracts, 2) if exit_spread > 0 else 0.0,
        step=1.0, format="%.2f",
        key=f"pnl_in_{trade_id}",
        help="P/L Open $ from ThinkorSwim — or leave as calculated",
    )
    reason = cl3.selectbox(
        "Exit reason",
        ["target_hit", "stop_hit", "rolled", "expiry", "manual_close", "assignment"],
        key=f"reason_{trade_id}",
    )

    if st.button("🔴 Close Trade", key=f"close_{trade_id}", type="primary"):
        ok = logger.close_trade(trade_id, exit_spread, pnl_input, reason)
        if ok:
            st.success(f"Trade `{trade_id}` closed — P&L ${pnl_input:+.2f}")
            st.rerun()
        else:
            st.error("Close failed — trade ID not found in log.")


# ─────────────────────────────────────────────
# Policy Lab + Research (sidebar toggles)
# ─────────────────────────────────────────────
def _render_policy_lab(enriched_rows, transition_queue):
    """Render what-if policy simulation panel."""
    try:
        from policy.policy_scenario_registry import POLICY_SCENARIOS
        from policy.policy_simulator import simulate_policy_scenario
        from policy.policy_diff_engine import build_policy_diff
        from policy.policy_report_renderer import render_policy_report
        import streamlit as st
        st.markdown("### 🧪 Policy Lab")
        key = st.selectbox("Scenario", list(POLICY_SCENARIOS.keys()),
                           format_func=lambda k: POLICY_SCENARIOS[k]["name"], key="pl_sel")
        if st.button("▶ Run", key="pl_run"):
            with st.spinner("Simulating..."):
                bundle = {"playbook_policy_registry":{},"playbook_capital_policy":{},
                          "symbol_concurrency_overrides":{},"execution_policy_overrides":{},
                          "surface_threshold_override":65.0}
                sim = simulate_policy_scenario(enriched_rows, bundle, POLICY_SCENARIOS[key]["overrides"])
                diff= build_policy_diff(transition_queue, sim["simulated_queue"],
                                         enriched_rows, sim["simulated_rows"])
                render_policy_report(POLICY_SCENARIOS[key]["name"], diff)
    except Exception as e:
        import streamlit as st; st.warning(f"Policy lab error: {e}")


def _render_research_panel():
    """Render playbook research report."""
    try:
        import streamlit as st
        from research.playbook_backtest_engine import run_playbook_backtest
        from research.playbook_report_renderer import render_playbook_report
        journals = st.session_state.get("transition_journals", [])
        pkg = run_playbook_backtest(journals)
        render_playbook_report(pkg)
    except Exception as e:
        import streamlit as st; st.info(f"Log transitions to populate research. ({e})")


# ─────────────────────────────────────────────
# Diagnostics + Validation (sidebar toggles)
# ─────────────────────────────────────────────
def _render_diagnostics(enriched_rows, transition_queue, slippage_model=None, playbook_stats=None):
    try:
        import streamlit as st
        from diagnostics.diagnostics_report_engine import build_diagnostics_report
        from diagnostics.diagnostics_renderer import render_diagnostics_report
        report = build_diagnostics_report(enriched_rows, transition_queue,
                                          slippage_model or {}, playbook_stats or {})
        render_diagnostics_report(report)
    except Exception as e:
        import streamlit as st; st.warning(f"Diagnostics: {e}")


def _render_validation_panel():
    try:
        import streamlit as st
        from tests.run_validation import run_all_validations
        if st.button("▶ Run Validation Suite", key="run_validation"):
            with st.spinner("Running all validation suites..."):
                result = run_all_validations()
            st.markdown(f"### Validation: **{result['total_pass']} passed** | **{result['total_fail']} failed**")
            import pandas as pd
            rows = [{"Suite":r["suite"],"Test":r.get("test","?"),
                     "Status":r.get("status","?"),"Error":r.get("error","")} for r in result["results"]]
            df = pd.DataFrame(rows)
            passed = df[df["Status"]=="PASS"]; failed = df[df["Status"]!="PASS"]
            if not failed.empty:
                st.error("Failures:")
                st.dataframe(failed, use_container_width=True, hide_index=True)
            st.success(f"✓ {len(passed)}/{len(rows)} checks passed")
            with st.expander("All results"):
                st.dataframe(df, use_container_width=True, hide_index=True)
    except Exception as e:
        import streamlit as st; st.warning(f"Validation panel error: {e}")


# ─────────────────────────────────────────────
# Environment banner (call at top of every render)
# ─────────────────────────────────────────────
def render_environment_banner(environment: str = "DEV") -> None:
    """Unmissable DEV/SIM/LIVE banner."""
    import streamlit as st
    COLORS = {"DEV":"#6b7280","SIM":"#2563eb","LIVE":"#15803d"}
    LABELS = {"DEV":"🔧 DEV — execution disabled",
              "SIM":"📋 SIM — paper environment (no live execution)",
              "LIVE":"🔴 LIVE — production environment"}
    env = str(environment).upper()
    color = COLORS.get(env,"#6b7280"); label = LABELS.get(env,env)
    st.markdown(f'<div style="padding:8px 16px;background:{color};color:#fff;'
                f'border-radius:8px;font-weight:700;margin-bottom:10px">{label}</div>',
                unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Monitoring / alerting helpers
# ─────────────────────────────────────────────
def _run_monitoring(enriched_rows, transition_queue, slippage_model, exposure_metrics, environment="DEV"):
    """Compute metrics, threshold alerts, and rollback watch."""
    try:
        from monitoring.metric_engine import compute_operational_metrics
        from monitoring.threshold_registry import get_thresholds
        from monitoring.alert_rule_engine import build_alerts
        from monitoring.alert_router import route_alert
        from monitoring.rollback_watch_engine import evaluate_rollback_watch

        metrics = compute_operational_metrics(enriched_rows, transition_queue,
                                              slippage_model or {}, {}, exposure_metrics or {})
        thresholds = get_thresholds(environment)
        alerts = [route_alert(a) for a in build_alerts(metrics, thresholds, environment)]
        rw_alerts = evaluate_rollback_watch(metrics, None)
        return metrics, alerts + rw_alerts
    except Exception as e:
        return {}, []


def _render_monitoring_panel(enriched_rows, transition_queue, slippage_model, exposure_metrics, environment="DEV"):
    try:
        import streamlit as st
        from monitoring.alert_renderer import render_alerts
        metrics, alerts = _run_monitoring(enriched_rows, transition_queue,
                                          slippage_model, exposure_metrics, environment)
        render_alerts(alerts)
        # Compact health strip
        if metrics:
            st.markdown("**Health Metrics**")
            c1,c2,c3,c4=st.columns(4)
            c1.metric("Queue Depth",int(metrics.get("queue_depth",0)))
            c2.metric("Block Rate",f'{metrics.get("blocked_candidate_rate",0)*100:.1f}%')
            c3.metric("Fill Score",f'{metrics.get("avg_fill_score_recent",0):.1f}')
            c4.metric("Top Sym %",f'{metrics.get("top_symbol_concentration",0)*100:.1f}%')
    except Exception as e:
        import streamlit as st; st.warning(f"Monitoring error: {e}")


# ─────────────────────────────────────────────
# History / snapshot helpers (sidebar toggle)
# ─────────────────────────────────────────────
def _render_trends_panel(snapshot_store):
    try:
        import streamlit as st
        from history.trend_engine import compute_metric_trend
        from history.trend_renderer import render_trend_block
        if not snapshot_store: st.info("No snapshots yet — trends populate after a few refreshes."); return
        queue_snaps=[s for s in snapshot_store if s.get("snapshot_type")=="QUEUE_SNAPSHOT"]
        exec_snaps =[s for s in snapshot_store if s.get("snapshot_type")=="EXECUTION_SNAPSHOT"]
        if queue_snaps:
            render_trend_block("Queue Depth", compute_metric_trend(queue_snaps,"queue_depth"))
        if exec_snaps:
            render_trend_block("Fill Score",  compute_metric_trend(exec_snaps,"avg_fill_score_recent"))
            render_trend_block("Delay Rate",  compute_metric_trend(exec_snaps,"delay_rate"))
    except Exception as e:
        import streamlit as st; st.warning(f"Trends error: {e}")
