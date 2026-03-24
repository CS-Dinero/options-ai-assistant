"""
engines/live_strike_selector.py
Generic live strike-selection module for put diagonals, call diagonals,
bull put credit spreads, and bear call credit spreads.

Works from live chain data (Massive/CSV/mock) for any symbol.
Symbol-specific behavior driven by SYMBOL_SELECTOR_CONFIG in vh_config.py.

Main entry point:
    candidates = build_live_roll_candidates(position, market_ctx, live_chain)

Output feeds directly into roll_credit_calculator.calculate_best_roll().
"""
from __future__ import annotations

import math
from typing import Any

from config.vh_config import (
    MIN_ROLL_NET_CREDIT, SYMBOL_SELECTOR_CONFIG,
    DEFAULT_SELECTOR_CONFIG,
)


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _sf(v: Any, d: float = 0.0) -> float:
    try:
        return float(v) if v not in (None, "", "—") else d
    except (TypeError, ValueError):
        return d


def _bid_ask_quality(bid: float, ask: float) -> float:
    """0–1 quality score. 1 = tight market, 0 = no market."""
    if ask <= 0:
        return 0.0
    spread = ask - bid
    mid    = (bid + ask) / 2.0
    if mid <= 0:
        return 0.0
    ratio = spread / mid
    if ratio <= 0.05:  return 1.0
    if ratio <= 0.10:  return 0.85
    if ratio <= 0.15:  return 0.65
    if ratio <= 0.25:  return 0.40
    if ratio <= 0.40:  return 0.20
    return 0.0


def _dte(expiration: str) -> int:
    """Compute DTE from ISO date string."""
    from datetime import date, datetime
    try:
        exp = datetime.strptime(expiration.strip(), "%Y-%m-%d").date()
        return max((exp - date.today()).days, 0)
    except Exception:
        return 0


def _get_sym_cfg(symbol: str) -> dict[str, Any]:
    """Return symbol-specific config, falling back to DEFAULT_SELECTOR_CONFIG."""
    return SYMBOL_SELECTOR_CONFIG.get(symbol.upper(), DEFAULT_SELECTOR_CONFIG)


# ─────────────────────────────────────────────
# CHAIN FILTERING
# ─────────────────────────────────────────────

def _filter_chain(
    chain:       list[dict],
    option_type: str,
    dte_min:     int,
    dte_max:     int,
) -> list[dict]:
    """Return rows matching option_type and DTE window, sorted by strike."""
    rows = [
        r for r in chain
        if str(r.get("option_type","")).lower() == option_type.lower()
        and dte_min <= int(_sf(r.get("dte"), _dte(str(r.get("expiration",""))))) <= dte_max
        and _sf(r.get("mid")) > 0
        and _sf(r.get("bid")) >= 0
    ]
    return sorted(rows, key=lambda r: _sf(r.get("strike")))


def _select_expirations(
    chain:           list[dict],
    short_dte_target: int = 7,
    long_dte_min:    int  = 21,
    long_dte_max:    int  = 45,
) -> list[tuple[str, str]]:
    """
    Find valid (short_exp, long_exp) pairs where:
      short_exp DTE ≈ short_dte_target (±5 days)
      long_exp  DTE ∈ [long_dte_min, long_dte_max]
      long DTE  > short DTE + 14 days minimum
    """
    all_exps = sorted(set(str(r.get("expiration","")) for r in chain if r.get("expiration")))
    pairs: list[tuple[str, str]] = []

    for short_exp in all_exps:
        s_dte = _dte(short_exp)
        if not (short_dte_target - 5 <= s_dte <= short_dte_target + 5):
            continue
        for long_exp in all_exps:
            l_dte = _dte(long_exp)
            if l_dte < long_dte_min or l_dte > long_dte_max:
                continue
            if l_dte <= s_dte + 14:
                continue
            pairs.append((short_exp, long_exp))

    return pairs


def _find_strikes_by_delta(
    chain:       list[dict],
    option_type: str,
    expiration:  str,
    delta_min:   float,
    delta_max:   float,
    spot:        float,
) -> list[dict]:
    """
    Find chain rows for a specific expiration within the delta band.
    Falls back to moneyness if delta is missing.
    """
    rows = [
        r for r in chain
        if str(r.get("option_type","")).lower() == option_type.lower()
        and str(r.get("expiration","")) == expiration
        and _sf(r.get("mid")) > 0
    ]
    if not rows:
        return []

    # Try delta-based selection
    delta_rows = [
        r for r in rows
        if r.get("delta") is not None
        and delta_min <= abs(_sf(r.get("delta"))) <= delta_max
    ]
    if delta_rows:
        return delta_rows

    # Fallback: moneyness-based approximation
    # For puts: OTM = strike < spot; target ~5–15% OTM for typical delta band
    low_pct  = 1.0 - delta_max * 1.2   # rough approximation
    high_pct = 1.0 - delta_min * 0.8
    low_k    = spot * low_pct
    high_k   = spot * high_pct

    moneyness_rows = [
        r for r in rows
        if (low_k <= _sf(r.get("strike")) <= high_k)
        if option_type == "put"
    ]
    if not moneyness_rows and option_type == "put":
        # Widen the net — just find OTM puts
        moneyness_rows = [r for r in rows if _sf(r.get("strike")) < spot * 0.99]

    return moneyness_rows


# ─────────────────────────────────────────────
# CANDIDATE SCORING
# ─────────────────────────────────────────────

def score_selector_candidate(
    candidate:    dict[str, Any],
    market_ctx:   dict[str, Any],
    symbol_config: dict[str, Any],
) -> float:
    """
    Score 0–100. Weights:
      liquidity quality    25
      credit attractiveness 25
      regime fit           20
      delta fit            15
      EM/distance fit      10
      expiration fit        5
    """
    score = 0.0

    # Liquidity (25)
    liq = _sf(candidate.get("liquidity_score"), 0.5)
    score += liq * 25.0

    # Credit attractiveness (25)
    credit = _sf(candidate.get("estimated_opening_credit_or_debit"))
    if credit >= 3.0:   score += 25.0
    elif credit >= 2.0: score += 20.0
    elif credit >= 1.0: score += 12.0
    elif credit > 0:    score +=  5.0
    # zero or negative = no points (debit = blocked downstream)

    # Regime fit (20)
    gamma    = str(market_ctx.get("gamma_regime","")).lower()
    struct   = str(candidate.get("target_structure","")).lower()
    iv       = str(market_ctx.get("iv_regime","")).lower()

    if "positive" in gamma:
        if "credit" in struct:      score += 20.0
        elif "diagonal" in struct:  score += 12.0
        else:                       score +=  5.0
    elif "negative" in gamma:
        if "diagonal" in struct:    score += 20.0
        elif "put" in struct:       score += 14.0
        else:                       score +=  5.0
    else:
        score += 10.0  # neutral — moderate points for any structure

    if "elevated" in iv or "extreme" in iv:
        score += 5.0  # bonus: selling into high IV

    # Delta fit (15)
    delta     = abs(_sf(candidate.get("estimated_short_delta")))
    d_min     = _sf(symbol_config.get("short_delta_min", 0.15))
    d_max     = _sf(symbol_config.get("short_delta_max", 0.35))
    if delta > 0:
        if d_min <= delta <= d_max:
            score += 15.0
        elif delta < d_min:
            score += max(0, 15.0 - (d_min - delta) * 80)
        else:
            score += max(0, 15.0 - (delta - d_max) * 80)

    # EM/distance fit (10)
    em   = _sf(market_ctx.get("expected_move"))
    spot = _sf(market_ctx.get("spot_price"))
    dist = _sf(candidate.get("distance_from_spot_pct"))
    if em > 0 and spot > 0:
        em_pct = em / spot
        if 0.5 * em_pct <= dist <= 1.5 * em_pct:
            score += 10.0  # short strike within 0.5–1.5 EM bands
        elif dist < 0.5 * em_pct:
            score += 5.0   # too close
        elif dist < 2.5 * em_pct:
            score += 7.0   # within 2.5 EM — acceptable

    # Expiration fit (5)
    l_dte = int(_sf(candidate.get("long_dte")))
    s_dte = int(_sf(candidate.get("short_dte")))
    if 7 <= s_dte <= 12 and 21 <= l_dte <= 40:
        score += 5.0
    elif 21 <= l_dte <= 45:
        score += 3.0

    return round(min(score, 100.0), 2)


# ─────────────────────────────────────────────
# CANDIDATE BUILDERS
# ─────────────────────────────────────────────

def _make_candidate(
    structure:   str,
    short_row:   dict,
    long_row:    dict,
    spot:        float,
) -> dict[str, Any] | None:
    """Build a candidate dict from two chain rows."""
    s_mid = _sf(short_row.get("mid"))
    l_mid = _sf(long_row.get("mid"))
    s_bid = _sf(short_row.get("bid"))
    s_ask = _sf(short_row.get("ask"))
    l_bid = _sf(long_row.get("bid"))
    l_ask = _sf(long_row.get("ask"))

    if s_mid <= 0 or l_mid <= 0:
        return None

    s_strike = _sf(short_row.get("strike"))
    l_strike = _sf(long_row.get("strike"))
    s_exp    = str(short_row.get("expiration",""))
    l_exp    = str(long_row.get("expiration",""))
    s_dte    = int(_sf(short_row.get("dte"), _dte(s_exp)))
    l_dte    = int(_sf(long_row.get("dte"), _dte(l_exp)))

    # Net credit: for diagonals, short_mid − long_mid (per share)
    # For credit spreads (same expiry), also short_mid − long_mid
    credit = round(s_mid - l_mid, 4)

    # Distance of short from spot
    dist_pct = abs(spot - s_strike) / spot if spot > 0 else 0.0

    # Liquidity quality (worst of the two legs)
    liq = min(_bid_ask_quality(s_bid, s_ask), _bid_ask_quality(l_bid, l_ask))

    # Roll-cycle heuristic (advisory only)
    rolls_to_free = None
    gold_harvest_eta = None
    if credit > 0 and s_dte > 0:
        # Rough: how many rolls until cumulative credit ≥ $5 gold threshold
        weekly_credit_est = round(s_mid * math.sqrt(7 / max(s_dte, 1)), 4)
        if weekly_credit_est > 0:
            rolls_to_free    = max(1, math.ceil(l_mid / weekly_credit_est))
            gold_harvest_eta = f"~week {max(1, math.ceil(5.0 / weekly_credit_est))}"

    return {
        "target_structure":               structure,
        "target_short_strike":            s_strike,
        "target_long_strike":             l_strike,
        "target_short_expiration":        s_exp,
        "target_long_expiration":         l_exp,
        "short_dte":                      s_dte,
        "long_dte":                       l_dte,
        "estimated_new_short_mid":        s_mid,
        "estimated_new_long_mid":         l_mid,
        "estimated_short_delta":          _sf(short_row.get("delta")),
        "estimated_long_delta":           _sf(long_row.get("delta")),
        "estimated_opening_credit_or_debit": credit,
        "distance_from_spot_pct":         round(dist_pct, 4),
        "liquidity_score":                round(liq, 3),
        "width":                          round(abs(s_strike - l_strike), 2),
        "rolls_to_free_heuristic":        rolls_to_free,
        "gold_harvest_eta_heuristic":     gold_harvest_eta,
        "selector_score":                 0.0,   # filled in after scoring
        "selector_rationale":             "",    # filled in after scoring
    }


def build_put_diagonal_candidates(
    chain:         list[dict],
    spot:          float,
    market_ctx:    dict[str, Any],
    symbol_config: dict[str, Any],
) -> list[dict[str, Any]]:
    """Short put (closer DTE) + long put (further DTE, same or lower strike)."""
    cfg       = symbol_config
    min_w     = _sf(cfg.get("min_width", 5))
    candidates: list[dict] = []

    pairs = _select_expirations(chain,
                                short_dte_target=7,
                                long_dte_min=21,
                                long_dte_max=45)

    for s_exp, l_exp in pairs:
        # Short leg: OTM puts in delta band
        short_rows = _find_strikes_by_delta(chain, "put", s_exp,
                                             _sf(cfg.get("short_delta_min", 0.15)),
                                             _sf(cfg.get("short_delta_max", 0.35)),
                                             spot)
        # Long leg: lower strike puts in the same or further expiry
        long_rows = [
            r for r in chain
            if str(r.get("option_type","")).lower() == "put"
            and str(r.get("expiration","")) == l_exp
            and _sf(r.get("mid")) > 0
        ]

        for sr in short_rows:
            for lr in long_rows:
                s_k = _sf(sr.get("strike"))
                l_k = _sf(lr.get("strike"))
                # Long strike must be <= short strike, width must meet minimum
                if l_k >= s_k:
                    continue
                if s_k - l_k < min_w:
                    continue
                c = _make_candidate("put_diagonal", sr, lr, spot)
                if c and c["estimated_opening_credit_or_debit"] >= MIN_ROLL_NET_CREDIT:
                    candidates.append(c)

    return candidates


def build_call_diagonal_candidates(
    chain:         list[dict],
    spot:          float,
    market_ctx:    dict[str, Any],
    symbol_config: dict[str, Any],
) -> list[dict[str, Any]]:
    """Short call (closer DTE, OTM) + long call (further DTE, same or higher strike)."""
    cfg       = symbol_config
    min_w     = _sf(cfg.get("min_width", 5))
    candidates: list[dict] = []

    pairs = _select_expirations(chain, short_dte_target=7, long_dte_min=21, long_dte_max=45)

    for s_exp, l_exp in pairs:
        short_rows = _find_strikes_by_delta(chain, "call", s_exp,
                                             _sf(cfg.get("short_delta_min", 0.15)),
                                             _sf(cfg.get("short_delta_max", 0.35)),
                                             spot)
        long_rows = [
            r for r in chain
            if str(r.get("option_type","")).lower() == "call"
            and str(r.get("expiration","")) == l_exp
            and _sf(r.get("mid")) > 0
        ]

        for sr in short_rows:
            for lr in long_rows:
                s_k = _sf(sr.get("strike"))
                l_k = _sf(lr.get("strike"))
                if l_k <= s_k:
                    continue
                if l_k - s_k < min_w:
                    continue
                c = _make_candidate("call_diagonal", sr, lr, spot)
                if c and c["estimated_opening_credit_or_debit"] >= MIN_ROLL_NET_CREDIT:
                    candidates.append(c)

    return candidates


def build_bull_put_credit_candidates(
    chain:         list[dict],
    spot:          float,
    market_ctx:    dict[str, Any],
    symbol_config: dict[str, Any],
) -> list[dict[str, Any]]:
    """Same-expiry put spread: sell higher OTM put, buy lower put."""
    cfg       = symbol_config
    min_w     = _sf(cfg.get("min_width", 5))
    candidates: list[dict] = []

    pairs = _select_expirations(chain, short_dte_target=7, long_dte_min=7, long_dte_max=14)
    # For same-expiry: use the short expiry for both legs
    exps = list(set(s for s, _ in pairs)) + [s for s, l in pairs if s == l]
    exps = sorted(set(
        exp for exp in set(str(r.get("expiration","")) for r in chain)
        if 3 <= _dte(exp) <= 14
    ))

    for exp in exps:
        short_rows = _find_strikes_by_delta(chain, "put", exp,
                                             _sf(cfg.get("short_delta_min", 0.15)),
                                             _sf(cfg.get("short_delta_max", 0.35)), spot)
        long_rows  = [r for r in chain
                      if str(r.get("option_type","")).lower() == "put"
                      and str(r.get("expiration","")) == exp
                      and _sf(r.get("mid")) > 0]

        for sr in short_rows:
            for lr in long_rows:
                s_k = _sf(sr.get("strike"))
                l_k = _sf(lr.get("strike"))
                if l_k >= s_k or s_k - l_k < min_w:
                    continue
                c = _make_candidate("bull_put_credit", sr, lr, spot)
                if c and c["estimated_opening_credit_or_debit"] >= MIN_ROLL_NET_CREDIT:
                    candidates.append(c)

    return candidates


def build_bear_call_credit_candidates(
    chain:         list[dict],
    spot:          float,
    market_ctx:    dict[str, Any],
    symbol_config: dict[str, Any],
) -> list[dict[str, Any]]:
    """Same-expiry call spread: sell lower OTM call, buy higher call."""
    cfg       = symbol_config
    min_w     = _sf(cfg.get("min_width", 5))
    candidates: list[dict] = []

    exps = sorted(set(
        exp for exp in set(str(r.get("expiration","")) for r in chain)
        if 3 <= _dte(exp) <= 14
    ))

    for exp in exps:
        short_rows = _find_strikes_by_delta(chain, "call", exp,
                                             _sf(cfg.get("short_delta_min", 0.15)),
                                             _sf(cfg.get("short_delta_max", 0.35)), spot)
        long_rows  = [r for r in chain
                      if str(r.get("option_type","")).lower() == "call"
                      and str(r.get("expiration","")) == exp
                      and _sf(r.get("mid")) > 0]

        for sr in short_rows:
            for lr in long_rows:
                s_k = _sf(sr.get("strike"))
                l_k = _sf(lr.get("strike"))
                if l_k <= s_k or l_k - s_k < min_w:
                    continue
                c = _make_candidate("bear_call_credit", sr, lr, spot)
                if c and c["estimated_opening_credit_or_debit"] >= MIN_ROLL_NET_CREDIT:
                    candidates.append(c)

    return candidates


# ─────────────────────────────────────────────
# RATIONALE BUILDER
# ─────────────────────────────────────────────

def _build_rationale(c: dict[str, Any]) -> str:
    score   = c.get("selector_score", 0)
    struct  = str(c.get("target_structure","")).replace("_"," ").title()
    credit  = _sf(c.get("estimated_opening_credit_or_debit"))
    width   = _sf(c.get("width"))
    delta   = abs(_sf(c.get("estimated_short_delta")))
    s_dte   = int(_sf(c.get("short_dte")))
    l_dte   = int(_sf(c.get("long_dte")))
    rolls   = c.get("rolls_to_free_heuristic")
    gold    = c.get("gold_harvest_eta_heuristic")

    parts = [
        f"{struct} at ${c.get('target_short_strike',0):.0f}/{c.get('target_long_strike',0):.0f}",
        f"opens for ${credit:.2f} net credit per share",
        f"${width:.0f} wide",
        f"short delta {delta:.2f}",
        f"{s_dte}/{l_dte} DTE",
    ]
    if rolls:
        parts.append(f"est. {rolls} rolls to recover long cost")
    if gold:
        parts.append(f"gold harvest {gold}")
    parts.append(f"score {score:.0f}/100")
    return " | ".join(parts) + "."


# ─────────────────────────────────────────────
# MAIN SELECTOR
# ─────────────────────────────────────────────

def build_live_roll_candidates(
    position:   dict[str, Any],
    market_ctx: dict[str, Any],
    live_chain: list[dict],
    config:     dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Generate and score all valid replacement structures from the live chain.

    Returns a list of scored candidates sorted best-first.
    Each candidate is in the format expected by roll_credit_calculator.calculate_best_roll().

    Parameters
    ----------
    position   : tracked position row (needs symbol, strategy_type, etc.)
    market_ctx : derived context (spot_price, gamma_regime, iv_regime, expected_move)
    live_chain : raw chain rows from any MarketDataProvider.get_chain()
    config     : optional override for SYMBOL_SELECTOR_CONFIG
    """
    symbol     = str(position.get("symbol","")).upper()
    spot       = _sf(market_ctx.get("spot_price") or position.get("live_spot"))
    sym_cfg    = (config or {}).get(symbol) if config else None
    sym_cfg    = sym_cfg or _get_sym_cfg(symbol)

    if spot <= 0 or not live_chain:
        return []

    # Build candidates for all four structure types
    all_candidates: list[dict] = []
    all_candidates.extend(build_put_diagonal_candidates(live_chain, spot, market_ctx, sym_cfg))
    all_candidates.extend(build_call_diagonal_candidates(live_chain, spot, market_ctx, sym_cfg))
    all_candidates.extend(build_bull_put_credit_candidates(live_chain, spot, market_ctx, sym_cfg))
    all_candidates.extend(build_bear_call_credit_candidates(live_chain, spot, market_ctx, sym_cfg))

    if not all_candidates:
        return []

    # Score all candidates
    for c in all_candidates:
        c["selector_score"] = score_selector_candidate(c, market_ctx, sym_cfg)

    # Deduplicate: keep best score per (structure, short_strike, short_exp)
    seen: dict[tuple, dict] = {}
    for c in all_candidates:
        key = (c["target_structure"], c["target_short_strike"], c["target_short_expiration"])
        if key not in seen or c["selector_score"] > seen[key]["selector_score"]:
            seen[key] = c

    # Build rationale now that scores are computed
    deduped = sorted(seen.values(), key=lambda x: x["selector_score"], reverse=True)
    for c in deduped:
        c["selector_rationale"] = _build_rationale(c)

    return deduped
