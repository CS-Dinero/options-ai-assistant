"""scanner/tradier_calendar_scanner.py — Fetch live Tradier chains and run deep ITM calendar scan.

Strategy context: Deep ITM calendars are used as ROLLING TOOLS, not cheapness plays.
The long leg builds intrinsic value. The short leg is sold repeatedly for net credit.
Filters are tuned to show viable roll candidates, not just "cheap" entries.
"""
from __future__ import annotations
from typing import Any
from scanner.deep_itm_entry_filters import OptionLegQuote, DeepITMEntryFilterConfig
from scanner.deep_itm_calendar_scanner import MarketContextLite, scan_deep_itm_calendar_candidates

# ── Roll-focused config — wide enough to surface $0.55-type entries ────────────
# User's edge: intrinsic value + roll continuity, not entry cheapness
DEFAULT_CFG = DeepITMEntryFilterConfig(
    long_delta_min=0.55,        # wider delta range — catch all meaningful ITM longs
    long_delta_max=0.98,
    short_dte_min=3,            # allow very short-dated shorts (weekly)
    short_dte_max=30,           # allow further-dated shorts for diagonals
    long_dte_min=15,            # allow tighter long legs when needed
    long_dte_max=120,           # allow LEAPS-style anchors
    min_open_interest=10,       # reduced — deep ITM has thinner markets
    min_volume=0,               # no volume gate — deep ITM often low volume
    max_bid_ask_width_pct=0.60, # wider spread ok — you work the mid
    max_entry_debit_width_ratio=0.80,  # much wider — debit/width ratio less important
    max_long_extrinsic_cost=25.0,      # allow high extrinsic on deep ITM longs
    min_projected_recovery_ratio=0.05, # nearly no gate — show the candidate, let user decide
    min_future_roll_score=10.0,        # minimal gate — show what's available
)

# Aggressive config for HIGH_VOL environments — show everything
AGGRESSIVE_CFG = DeepITMEntryFilterConfig(
    long_delta_min=0.40, long_delta_max=0.99,
    short_dte_min=1, short_dte_max=45,
    long_dte_min=7, long_dte_max=180,
    min_open_interest=1, min_volume=0,
    max_bid_ask_width_pct=0.99,
    max_entry_debit_width_ratio=2.00,
    max_long_extrinsic_cost=100.0,
    min_projected_recovery_ratio=0.01,
    min_future_roll_score=1.0,
)

REGIME_SCORE_MAP = {
    "NEUTRAL_TIME_SPREADS": 85.0,
    "LOW_VOL_NEUTRAL":      78.0,
    "TRENDING":             65.0,
    "PREMIUM_SELLING":      55.0,
    "HIGH_VOL_UNSTABLE":    50.0,   # was 30 — still show candidates, user decides
}

def _to_leg_quotes(chain: list[dict], option_type: str) -> list[OptionLegQuote]:
    ot = option_type.upper()
    quotes = []
    for row in chain:
        if row.get("option_type","").lower() != ot.lower():
            continue
        mid = float(row.get("mid") or 0)
        if mid <= 0:
            continue
        quotes.append(OptionLegQuote(
            symbol=row["symbol"], option_type=ot, expiry=row["expiration"],
            strike=float(row.get("strike",0)), bid=float(row.get("bid") or 0),
            ask=float(row.get("ask") or 0), mid=mid, delta=row.get("delta"),
            open_interest=int(row.get("open_interest") or 0),
            volume=int(row.get("volume") or 0),
        ))
    return quotes


def scan_deep_itm_calendars_live(
    symbol: str,
    option_type: str = "PUT",
    environment: str = "NEUTRAL_TIME_SPREADS",
    regime_alignment_score: float | None = None,
    aggressive: bool = False,
    cfg: DeepITMEntryFilterConfig | None = None,
    session=None,
) -> list[dict]:
    from data_sources.tradier_api import (
        get_spot_price, get_expirations, get_option_chain,
        pick_short_expiration, pick_long_expiration, TradierAPIError,
    )
    from datetime import date

    # Use aggressive config in high-vol or when user requests it
    if cfg is None:
        cfg = AGGRESSIVE_CFG if (aggressive or environment == "HIGH_VOL_UNSTABLE") else DEFAULT_CFG

    regime_score = regime_alignment_score or REGIME_SCORE_MAP.get(environment, 60.0)
    today_str = date.today().isoformat()
    ot = option_type.upper()

    try:
        spot = get_spot_price(symbol, session=session)
    except TradierAPIError as e:
        return [{"error": f"Spot price fetch failed: {e}", "symbol": symbol}]

    try:
        expirations = get_expirations(symbol, session=session)
    except TradierAPIError as e:
        return [{"error": f"Expiration fetch failed: {e}", "symbol": symbol}]

    if not expirations:
        return [{"error": f"No expirations for {symbol}", "symbol": symbol}]

    # Build candidate leg pairs across ALL available expiry combos
    # Not just one short/long pair — scan all short exps against all long exps
    sorted_exps = sorted(expirations)

    # Short candidates: first 4 expirations (near-dated shorts)
    short_exps = sorted_exps[:6]
    # Long candidates: expirations from 2 weeks out to 4 months
    from datetime import datetime, timedelta
    today = date.today()
    long_exps = [e for e in sorted_exps
                 if (datetime.strptime(e,"%Y-%m-%d").date() - today).days >= 14][:8]

    if not long_exps:
        long_exps = sorted_exps[-3:]  # fallback

    # Fetch chains for all relevant expiries
    chains: dict[str, list[dict]] = {}
    for exp in set(short_exps + long_exps):
        try:
            chains[exp] = get_option_chain(symbol, exp, session=session)
        except TradierAPIError:
            chains[exp] = []

    # Estimate expected move from nearest ATM straddle
    expected_move = 0.0
    if short_exps and chains.get(short_exps[0]):
        c = chains[short_exps[0]]
        calls = [r for r in c if r.get("option_type","").lower()=="call" and float(r.get("mid") or 0)>0]
        puts  = [r for r in c if r.get("option_type","").lower()=="put"  and float(r.get("mid") or 0)>0]
        if calls and puts:
            ac = min(calls, key=lambda r: abs(float(r.get("strike",0))-spot))
            ap = min(puts,  key=lambda r: abs(float(r.get("strike",0))-spot))
            expected_move = round((float(ac.get("mid",0)) + float(ap.get("mid",0))) * 0.85, 2)

    ctx = MarketContextLite(symbol=symbol, spot_price=spot, expected_move=max(expected_move, spot*0.01),
                             iv_percentile=50.0, gamma_regime="POSITIVE", environment=environment,
                             regime_alignment_score=regime_score, as_of_date=today_str)

    # Run scan across all short/long expiry combos and collect all candidates
    all_candidates = []
    for long_exp in long_exps:
        long_legs  = _to_leg_quotes(chains.get(long_exp,[]), ot)
        # Filter to ITM longs (delta threshold relaxed)
        long_legs = [q for q in long_legs if q.delta is not None and abs(q.delta) >= 0.40]
        if not long_legs:
            continue

        for short_exp in short_exps:
            if short_exp >= long_exp:
                continue
            short_legs = _to_leg_quotes(chains.get(short_exp,[]), ot)
            next_exps  = [e for e in sorted_exps if e > short_exp and e <= long_exp]
            next_gen   = _to_leg_quotes(chains.get(next_exps[0],[]) if next_exps else [], ot)

            if not short_legs:
                continue

            candidates = scan_deep_itm_calendar_candidates(
                context=ctx, option_type=ot, long_leg_quotes=long_legs,
                short_leg_quotes=short_legs, candidate_next_shorts=next_gen, cfg=cfg,
            )
            all_candidates.extend(candidates)

    if not all_candidates:
        return [{"error": f"No deep ITM calendar candidates found for {symbol} (spot=${spot:.2f}). "
                          f"Try switching Option Type or check if market is open.", "symbol": symbol}]

    # De-duplicate by (long_strike, long_expiry, short_strike, short_expiry), keep best score
    seen: dict[tuple, Any] = {}
    for c in all_candidates:
        key = (c.long_leg["strike"], c.long_leg["expiry"], c.short_leg["strike"], c.short_leg["expiry"])
        if key not in seen or c.candidate_score > seen[key].candidate_score:
            seen[key] = c

    ranked = sorted(seen.values(), key=lambda c: c.candidate_score, reverse=True)

    results = []
    for c in ranked[:15]:
        results.append({
            "symbol":c.symbol, "option_type":c.option_type, "structure":c.structure,
            "spot_price":spot, "expected_move":expected_move,
            "long_strike":c.long_leg["strike"], "long_expiry":c.long_leg["expiry"],
            "long_mid":c.long_leg["mid"], "long_delta":c.long_leg["delta"],
            "short_strike":c.short_leg["strike"], "short_expiry":c.short_leg["expiry"],
            "short_mid":c.short_leg["mid"], "short_delta":c.short_leg["delta"],
            "short_dte":c.short_dte, "long_dte":c.long_dte, "strike_width":c.strike_width,
            "entry_net_debit":c.entry_net_debit,
            "entry_debit_width_ratio":c.entry_debit_width_ratio,
            "long_intrinsic_value":c.long_intrinsic_value,
            "long_extrinsic_cost":c.long_extrinsic_cost,
            "projected_recovery_ratio":c.projected_recovery_ratio,
            "future_roll_score":c.future_roll_score,
            "entry_cheapness_score":c.entry_cheapness_score,
            "expected_move_clearance":c.expected_move_clearance,
            "liquidity_score":c.liquidity_score,
            "candidate_score":c.candidate_score,
            "notes":c.notes,
        })
    return results
