"""scanner/tradier_calendar_scanner.py — Fetch live option data from Tradier and run deep ITM calendar scan.

Call scan_deep_itm_calendars_live() from the dashboard or CLI.
Returns DeepITMCalendarCandidate objects ranked by candidate_score.
"""
from __future__ import annotations
from typing import Any

from scanner.deep_itm_entry_filters import OptionLegQuote, DeepITMEntryFilterConfig
from scanner.deep_itm_calendar_scanner import (
    MarketContextLite, scan_deep_itm_calendar_candidates,
)


# ── Default filter config for live scanning ───────────────────────────────────
DEFAULT_CFG = DeepITMEntryFilterConfig(
    long_delta_min=0.70, long_delta_max=0.92,
    short_dte_min=5, short_dte_max=21,
    long_dte_min=30, long_dte_max=90,
    min_open_interest=50, min_volume=5,
    max_bid_ask_width_pct=0.30,
    max_entry_debit_width_ratio=0.42,
    max_long_extrinsic_cost=12.0,
    min_projected_recovery_ratio=0.50,
    min_future_roll_score=40.0,
)

# Regime alignment score assigned based on environment tag
REGIME_SCORE_MAP = {
    "NEUTRAL_TIME_SPREADS": 85.0,
    "LOW_VOL_NEUTRAL":      78.0,
    "TRENDING":             60.0,
    "PREMIUM_SELLING":      50.0,
    "HIGH_VOL_UNSTABLE":    30.0,
}

def _chain_rows_to_leg_quotes(chain: list[dict], option_type: str) -> list[OptionLegQuote]:
    """Convert raw chain rows to OptionLegQuote objects."""
    quotes = []
    ot = option_type.upper()
    for row in chain:
        if row.get("option_type","").upper() != ot.lower() and row.get("option_type","") != ot.lower():
            continue
        mid = float(row.get("mid") or 0)
        if mid <= 0:
            continue
        quotes.append(OptionLegQuote(
            symbol=row["symbol"],
            option_type=ot,
            expiry=row["expiration"],
            strike=float(row.get("strike", 0)),
            bid=float(row.get("bid") or 0),
            ask=float(row.get("ask") or 0),
            mid=mid,
            delta=row.get("delta"),
            open_interest=int(row.get("open_interest") or 0),
            volume=int(row.get("volume") or 0),
        ))
    return quotes


def scan_deep_itm_calendars_live(
    symbol: str,
    option_type: str = "PUT",
    environment: str = "NEUTRAL_TIME_SPREADS",
    regime_alignment_score: float | None = None,
    cfg: DeepITMEntryFilterConfig | None = None,
    session=None,
) -> list[dict]:
    """
    Fetch live data from Tradier and return ranked deep ITM calendar candidates.

    Returns list of dicts (serializable for Streamlit display).
    Returns [] with a descriptive error key if data unavailable.
    """
    from data_sources.tradier_api import (
        get_spot_price, get_expirations, get_option_chain,
        pick_short_expiration, pick_long_expiration, TradierAPIError,
    )
    from datetime import date

    cfg = cfg or DEFAULT_CFG
    regime_score = regime_alignment_score or REGIME_SCORE_MAP.get(environment, 60.0)
    today_str = date.today().isoformat()

    # ── 1. Spot price ─────────────────────────────────────────────────────────
    try:
        spot = get_spot_price(symbol, session=session)
    except TradierAPIError as e:
        return [{"error": f"Spot price fetch failed: {e}", "symbol": symbol}]

    # ── 2. Expirations ────────────────────────────────────────────────────────
    try:
        expirations = get_expirations(symbol, session=session)
    except TradierAPIError as e:
        return [{"error": f"Expiration fetch failed: {e}", "symbol": symbol}]

    if not expirations:
        return [{"error": f"No expirations available for {symbol}", "symbol": symbol}]

    short_exp = pick_short_expiration(expirations)
    long_exp  = pick_long_expiration(expirations)

    if not short_exp or not long_exp or short_exp == long_exp:
        return [{"error": f"Could not select valid short/long expirations for {symbol}", "symbol": symbol}]

    # ── 3. Option chains ──────────────────────────────────────────────────────
    try:
        short_chain = get_option_chain(symbol, short_exp, session=session)
        long_chain  = get_option_chain(symbol, long_exp,  session=session)
    except TradierAPIError as e:
        return [{"error": f"Chain fetch failed: {e}", "symbol": symbol}]

    if not short_chain or not long_chain:
        return [{"error": f"Empty chain data for {symbol}", "symbol": symbol}]

    # ── 4. Build next-gen short quotes (next expiration after short) ──────────
    next_exps = [e for e in sorted(expirations) if e > short_exp]
    next_gen_chain = []
    if next_exps:
        try:
            next_gen_chain = get_option_chain(symbol, next_exps[0], session=session)
        except TradierAPIError:
            pass  # not fatal — continuity score will be low

    ot = option_type.upper()
    long_legs    = _chain_rows_to_leg_quotes(long_chain,    ot)
    short_legs   = _chain_rows_to_leg_quotes(short_chain,   ot)
    next_gen_legs= _chain_rows_to_leg_quotes(next_gen_chain, ot)

    # Filter to deep ITM longs only (|delta| >= 0.65 as pre-filter)
    long_legs = [q for q in long_legs if q.delta is not None and abs(q.delta) >= 0.65]

    if not long_legs or not short_legs:
        return [{"error": f"No qualifying {ot} legs found for {symbol} (spot=${spot:.2f})", "symbol": symbol}]

    # ── 5. Market context ─────────────────────────────────────────────────────
    # Use ATM short-exp straddle to estimate expected move
    atm_calls = [q for q in _chain_rows_to_leg_quotes(short_chain,"CALL") if q.mid>0]
    atm_puts  = [q for q in short_legs if q.mid>0]
    expected_move = 0.0
    if atm_calls and atm_puts:
        atm_c = min(atm_calls, key=lambda q: abs(q.strike - spot))
        atm_p = min(atm_puts,  key=lambda q: abs(q.strike - spot))
        expected_move = round((atm_c.mid + atm_p.mid) * 0.85, 2)  # ~1 SD approximation

    ctx = MarketContextLite(
        symbol=symbol, spot_price=spot, expected_move=expected_move,
        iv_percentile=50.0,  # placeholder — can wire IV rank later
        gamma_regime="POSITIVE",
        environment=environment,
        regime_alignment_score=regime_score,
        as_of_date=today_str,
    )

    # ── 6. Scan candidates ────────────────────────────────────────────────────
    candidates = scan_deep_itm_calendar_candidates(
        context=ctx, option_type=ot,
        long_leg_quotes=long_legs, short_leg_quotes=short_legs,
        candidate_next_shorts=next_gen_legs, cfg=cfg,
    )

    if not candidates:
        return [{"error": f"No deep ITM calendar candidates passed filters for {symbol} (spot=${spot:.2f})", "symbol": symbol}]

    # ── 7. Serialize ──────────────────────────────────────────────────────────
    results = []
    for c in candidates[:10]:   # top 10 max
        results.append({
            "symbol": c.symbol,
            "option_type": c.option_type,
            "structure": c.structure,
            "spot_price": spot,
            "expected_move": expected_move,
            "long_strike": c.long_leg["strike"],
            "long_expiry": c.long_leg["expiry"],
            "long_mid": c.long_leg["mid"],
            "long_delta": c.long_leg["delta"],
            "short_strike": c.short_leg["strike"],
            "short_expiry": c.short_leg["expiry"],
            "short_mid": c.short_leg["mid"],
            "short_delta": c.short_leg["delta"],
            "short_dte": c.short_dte,
            "long_dte": c.long_dte,
            "strike_width": c.strike_width,
            "entry_net_debit": c.entry_net_debit,
            "entry_debit_width_ratio": c.entry_debit_width_ratio,
            "long_intrinsic_value": c.long_intrinsic_value,
            "long_extrinsic_cost": c.long_extrinsic_cost,
            "projected_recovery_ratio": c.projected_recovery_ratio,
            "future_roll_score": c.future_roll_score,
            "entry_cheapness_score": c.entry_cheapness_score,
            "expected_move_clearance": c.expected_move_clearance,
            "liquidity_score": c.liquidity_score,
            "candidate_score": c.candidate_score,
            "notes": c.notes,
        })
    return results
