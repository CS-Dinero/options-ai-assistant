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
from engines.gamma_engine   import classify_gamma_regime
from strategies.bear_call       import generate_bear_call_spreads
from strategies.bull_put        import generate_bull_put_spreads
from strategies.bull_call_debit import generate_bull_call_debit_spreads
from strategies.bear_put_debit  import generate_bear_put_debit_spreads
from calculator.trade_scoring   import rank_candidates, get_score_breakdown
from config.settings            import SCORE_STRONG, SCORE_TRADABLE


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
        "cheap":         "#22c55e",
        "moderate":      "#f59e0b",
        "elevated":      "#f97316",
        "rich":          "#ef4444",
        "contango":      "#22c55e",
        "flat":          "#f59e0b",
        "backwardation": "#ef4444",
        "positive":      "#22c55e",
        "neutral":       "#f59e0b",
        "negative":      "#ef4444",
        "unknown":       "#6b7280",
        "high_put_skew": "#f97316",
        "normal_skew":   "#22c55e",
        "flat_skew":     "#f59e0b",
        "rising":        "#ef4444",
        "falling":       "#22c55e",
        "flat":          "#f59e0b",
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

def build_derived(market: dict) -> dict:
    em_result = compute_expected_move(
        spot         = market["spot_price"],
        atm_call_mid = market.get("atm_call_mid"),
        atm_put_mid  = market.get("atm_put_mid"),
        iv_percent   = market.get("front_iv", 16.0),
        dte          = market.get("front_dte", 7),
    )
    term_slope = compute_term_slope(
        market.get("front_iv", 16.0),
        market.get("back_iv",  16.0),
    )
    skew_val = compute_skew(
        market.get("put_25d_iv"),
        market.get("call_25d_iv"),
    )
    return {
        "expected_move": em_result["expected_move"],
        "upper_em":      em_result["upper_em"],
        "lower_em":      em_result["lower_em"],
        "em_method":     em_result["method"],
        "atr_trend":      classify_atr_trend(
                              market.get("atr_14", 3.0),
                              market.get("atr_prior", 3.0)),
        "iv_regime":      classify_iv_regime(market.get("iv_percentile", 50.0)),
        "term_slope":     term_slope,
        "term_structure": classify_term_structure(term_slope),
        "skew_value":     skew_val,
        "skew_state":     classify_skew(skew_val),
        "gamma_regime":   classify_gamma_regime(market.get("total_gex")),
        "em_atr_ratio":   em_atr_ratio(
                              em_result["expected_move"],
                              market.get("atr_14", 3.0)),
        "gamma_flip":     market.get("gamma_flip"),
        "gamma_trap":     market.get("gamma_trap_strike"),
    }


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

    # Regime badges row
    col1, col2, col3, col4, col5, col6 = st.columns(6)

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
        st.markdown("**EM Method**")
        m = derived["em_method"]
        st.markdown(colored_badge(m.upper().replace("_", " "), "#3b82f6"), unsafe_allow_html=True)
        gt = derived.get("gamma_trap")
        st.caption(f"Trap: ${gt:.0f}" if gt else "Trap: N/A")


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

        if t["strategy_type"] in ("bear_call", "bull_put"):
            mc1.metric("Short Strike", f"${t['short_strike']:.0f}",
                       delta=f"Δ {t['short_delta']:.2f}")
            mc2.metric("Long Strike",  f"${t['hedge_strike']:.0f}",
                       delta=f"Δ {t['hedge_delta']:.2f}")
            mc3.metric("Credit",       f"${credit:.2f}",
                       delta=f"${credit*100:.0f}/contract")
            mc4.metric("Expiration",   t["short_expiration"])
        else:
            mc1.metric("Long Strike",  f"${t['long_strike']:.0f}",
                       delta=f"Δ {t['long_delta']:.2f}")
            mc2.metric("Short Strike", f"${t['short_strike']:.0f}",
                       delta=f"Δ {t['short_delta']:.2f}")
            mc3.metric("Debit",        f"${abs(credit):.2f}",
                       delta=f"${abs(credit)*100:.0f}/contract")
            mc4.metric("Expiration",   t["short_expiration"])

        # Risk row
        rc1, rc2, rc3, rc4, rc5 = st.columns(5)
        rc1.metric("Max Profit",   f"${t['max_profit']:.0f}")
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
    derived    = build_derived(market)
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


if __name__ == "__main__":
    main()
