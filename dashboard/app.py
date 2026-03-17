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
from dotenv import load_dotenv

# ── Path setup — works locally and on Streamlit Cloud ────────────────────────
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

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

        symbol = st.selectbox(
            "Underlying",
            ["SPY", "QQQ", "IWM", "AAPL", "MSFT", "TSLA"],
            index=0,
        )

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
    tlog_tab, bt_tab = st.tabs(["📋 Trade Log & Export", "🔬 Backtest"])

    with tlog_tab:
        _render_trade_log_panel(candidates, market, derived)

    with bt_tab:
        _render_backtest_panel()


if __name__ == "__main__":
    main()


# ─────────────────────────────────────────────
# TRADE LOG PANEL
# ─────────────────────────────────────────────

def _render_trade_log_panel(ranked: list[dict], market: dict, derived: dict):
    """
    Trade Log tab — visible, always expanded, three sub-tabs.
    """
    logger = TradeLogger()

    log_tab, positions_tab, stats_tab = st.tabs(
        ["📤 Log Scan", "📂 Open Positions", "📊 Performance Stats"]
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
                    c3.metric("Target", f"${t.get('target_price', '')}")
                    c4.metric("Score", t.get("score", ""))
                    st.caption(
                        f"Opened {t['date_open']} | "
                        f"Exp {t.get('short_expiration', '')} | "
                        f"ID: `{t['trade_id']}`"
                    )
                    with st.expander("Close this trade"):
                        ec1, ec2, ec3 = st.columns(3)
                        exit_px = ec1.number_input("Exit price", value=0.0, step=0.01, key=f"ep_{t['trade_id']}")
                        pnl_val = ec2.number_input("P&L ($)", value=0.0, step=1.0,    key=f"pnl_{t['trade_id']}")
                        reason  = ec3.selectbox("Reason",
                            ["target_hit", "stop_hit", "expiry", "manual_close", "rolled"],
                            key=f"r_{t['trade_id']}")
                        if st.button("Confirm close", key=f"close_{t['trade_id']}", type="primary"):
                            ok = logger.close_trade(t["trade_id"], exit_px, pnl_val, reason)
                            if ok:
                                st.success(f"Trade {t['trade_id']} closed")
                                st.rerun()

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
