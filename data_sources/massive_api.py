"""
data_sources/massive_api.py
Massive (formerly Polygon.io) API adapter.

Massive rebranded from Polygon.io in late 2025.
The API structure is identical — same endpoints, same response schema.
Base URL: https://api.massive.com  (same as api.polygon.io)

Authentication: API key passed as ?apiKey= query parameter.

Key advantage over Tradier:
  - Single chain snapshot call returns the ENTIRE options chain
    (all strikes, all expirations) in one request
  - Greeks and IV included on options plans
  - Pagination via next_url cursor for large chains (SPY has 5000+ rows)

Environment variables required:
    MASSIVE_API_KEY   — your API key from massive.com/dashboard/keys

Add to your .env file:
    MASSIVE_API_KEY=your_key_here

Endpoint used:
    GET /v3/snapshot/options/{underlyingAsset}
    Params: expiration_date, contract_type, limit, apiKey

Response shape per result:
    {
      "details": {
        "contract_type": "call",
        "expiration_date": "2026-03-21",
        "strike_price": 530.0,
        "ticker": "O:SPY260321C00530000"
      },
      "greeks": {
        "delta": 0.22,
        "gamma": 0.018,
        "theta": -0.21,
        "vega": 0.08
      },
      "implied_volatility": 0.168,   <- decimal, we convert to pct
      "last_quote": {
        "bid": 1.45,
        "ask": 1.52,
        "midpoint": 1.485
      },
      "day": {
        "volume": 6220
      },
      "open_interest": 15420
    }
"""

import os
import time
from datetime import date, datetime, timedelta
from typing import Any, Optional

try:
    import requests
    _REQUESTS_AVAILABLE = True
except ImportError:
    _REQUESTS_AVAILABLE = False

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

MASSIVE_API_KEY  = os.getenv("MASSIVE_API_KEY", "")

# Streamlit Cloud: load from st.secrets if env var not set
def _load_from_streamlit_secrets():
    global MASSIVE_API_KEY
    if not MASSIVE_API_KEY:
        try:
            import streamlit as st
            MASSIVE_API_KEY = st.secrets.get("MASSIVE_API_KEY", "")
        except Exception:
            pass

_load_from_streamlit_secrets()
MASSIVE_BASE_URL = "https://api.polygon.io"

# Chain snapshot: max rows per page (API max = 250)
PAGE_LIMIT = 250

# DTE window for long-leg expiration selection
LONG_DTE_MIN = 45
LONG_DTE_MAX = 75


# ─────────────────────────────────────────────
# EXCEPTIONS
# ─────────────────────────────────────────────

class MassiveAPIError(Exception):
    """Raised on auth failures, HTTP errors, or malformed responses."""
    pass


class MassiveDataError(Exception):
    """Raised when a response is clean but contains no usable data."""
    pass


# ─────────────────────────────────────────────
# INTERNAL HTTP HELPERS
# ─────────────────────────────────────────────

def _api_key() -> str:
    if not MASSIVE_API_KEY:
        raise MassiveAPIError(
            "MASSIVE_API_KEY environment variable is not set. "
            "Get your key from massive.com/dashboard/keys "
            "and add it to your .env file."
        )
    return MASSIVE_API_KEY


def _get(path: str, params: Optional[dict] = None, session=None) -> dict:
    """
    Execute a GET request against the Massive API.
    Injects apiKey automatically — never expose it in logs.
    """
    if not _REQUESTS_AVAILABLE:
        raise MassiveAPIError(
            "'requests' package not installed. Run: pip install requests"
        )

    client  = session or requests
    url     = f"{MASSIVE_BASE_URL}{path}"
    p       = dict(params or {})
    p["apiKey"] = _api_key()

    try:
        resp = client.get(url, params=p, timeout=30)
    except Exception as exc:
        raise MassiveAPIError(f"Network error reaching Massive: {exc}") from exc

    if resp.status_code == 403:
        raise MassiveAPIError(
            "Massive API returned 403 Forbidden. "
            "Check your API key and plan — Greeks require an options-enabled plan."
        )
    if resp.status_code == 429:
        raise MassiveAPIError(
            "Massive API rate limit hit. Wait 60 seconds and retry."
        )
    if resp.status_code >= 400:
        raise MassiveAPIError(
            f"Massive HTTP {resp.status_code} on {path}: {resp.text[:300]}"
        )

    try:
        return resp.json()
    except Exception as exc:
        raise MassiveAPIError(f"Non-JSON response from Massive: {exc}") from exc


def _get_paginated(path: str, params: dict, session=None) -> list[dict]:
    """
    Fetch all pages from a paginated Massive endpoint.
    Follows next_url cursor until exhausted.
    Rate-limit safe: 300ms delay between pages.
    """
    results = []
    current_params = dict(params)

    while True:
        payload = _get(path, current_params, session)
        page_results = payload.get("results", [])
        results.extend(page_results)

        next_url = payload.get("next_url")
        if not next_url:
            break

        # next_url is a full URL — extract path+params
        # Strip base URL and re-request with just the cursor
        cursor = _extract_cursor(next_url)
        if not cursor:
            break

        current_params = {"cursor": cursor, "limit": PAGE_LIMIT}
        time.sleep(0.3)   # respect rate limits

    return results


def _extract_cursor(next_url: str) -> Optional[str]:
    """Pull the cursor parameter out of a next_url string."""
    if "cursor=" in next_url:
        for part in next_url.split("&"):
            if part.startswith("cursor="):
                return part.split("=", 1)[1]
    return None


# ─────────────────────────────────────────────
# TYPE-SAFE FIELD PARSERS
# ─────────────────────────────────────────────

def _safe_float(value: Any) -> Optional[float]:
    try:
        if value in (None, "", "null", "N/A"):
            return None
        f = float(value)
        return f if f != 0.0 else None
    except (TypeError, ValueError):
        return None


def _safe_float_zero(value: Any) -> float:
    """Float with 0.0 fallback — for bid/ask where zero is valid."""
    try:
        if value in (None, "", "null"):
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _safe_int(value: Any) -> int:
    try:
        if value in (None, "", "null"):
            return 0
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _compute_mid(bid: float, ask: float, midpoint: Optional[float] = None) -> float:
    """
    Mid price with fallback chain:
      1. API-provided midpoint (most accurate)
      2. (bid + ask) / 2
      3. bid alone
      4. ask alone
      5. 0.0
    """
    if midpoint is not None and midpoint > 0:
        return round(midpoint, 4)
    if bid > 0 and ask > 0:
        return round((bid + ask) / 2.0, 4)
    if bid > 0:
        return round(bid, 4)
    if ask > 0:
        return round(ask, 4)
    return 0.0


def _compute_dte(expiration: str) -> int:
    try:
        exp = datetime.strptime(expiration, "%Y-%m-%d").date()
        return max(0, (exp - date.today()).days)
    except ValueError:
        return 0


# ─────────────────────────────────────────────
# ROW NORMALIZER
# ─────────────────────────────────────────────

def _normalize_result(raw: dict, symbol: str) -> Optional[dict]:
    """
    Normalize a single Massive snapshot result into the shared option_row schema.

    Massive response structure:
      raw["details"]          — contract metadata
      raw["greeks"]           — delta, gamma, theta, vega
      raw["implied_volatility"] — IV as decimal (0.168 = 16.8%)
      raw["last_quote"]       — bid, ask, midpoint
      raw["day"]              — volume, vwap, close
      raw["open_interest"]    — integer

    Greeks are kept as None when missing — scorer handles via reweighting.
    IV is converted from decimal to percentage to match mock schema.
    """
    details = raw.get("details") or {}
    greeks  = raw.get("greeks")  or {}
    quote   = raw.get("last_quote") or {}
    day     = raw.get("day") or {}

    expiration  = details.get("expiration_date", "")
    opt_type    = str(details.get("contract_type", "")).lower()
    strike      = _safe_float_zero(details.get("strike_price", 0))

    if not expiration or not opt_type or strike <= 0:
        return None   # skip malformed rows

    bid      = _safe_float_zero(quote.get("bid"))
    ask      = _safe_float_zero(quote.get("ask"))
    midpoint = _safe_float(quote.get("midpoint"))

    # When market is closed (weekend/after-hours) bid/ask are 0.
    # Fall back to previous session close so strategies can still run.
    mid = _compute_mid(bid, ask, midpoint)
    if mid == 0.0:
        prev_close = _safe_float(day.get("close"))
        if prev_close and prev_close > 0:
            mid = prev_close

    # IV: Massive returns as decimal — convert to percentage
    iv_raw = _safe_float(raw.get("implied_volatility"))
    iv     = round(iv_raw * 100, 4) if iv_raw else None

    return {
        "symbol":        symbol.upper(),
        "expiration":    expiration,
        "dte":           _compute_dte(expiration),
        "option_type":   opt_type,
        "strike":        strike,
        "bid":           bid,
        "ask":           ask,
        "mid":           mid,
        "delta":         _safe_float(greeks.get("delta")),
        "gamma":         _safe_float(greeks.get("gamma")),
        "theta":         _safe_float(greeks.get("theta")),
        "vega":          _safe_float(greeks.get("vega")),
        "iv":            iv,
        "open_interest": _safe_int(raw.get("open_interest")),
        "volume":        _safe_int(day.get("volume")),
    }


# ─────────────────────────────────────────────
# EXPIRATION HELPERS
# ─────────────────────────────────────────────

def pick_short_expiration(expirations: list[str]) -> Optional[str]:
    """Nearest expiration >= 5 DTE."""
    for exp in sorted(expirations):
        if _compute_dte(exp) >= 5:
            return exp
    return expirations[0] if expirations else None


def pick_long_expiration(expirations: list[str]) -> Optional[str]:
    """Expiration closest to 60 DTE within the 45–75 DTE window."""
    target = (LONG_DTE_MIN + LONG_DTE_MAX) // 2
    best, best_dist = None, float("inf")

    for exp in expirations:
        dte  = _compute_dte(exp)
        dist = abs(dte - target)
        if LONG_DTE_MIN <= dte <= LONG_DTE_MAX and dist < best_dist:
            best, best_dist = exp, dist

    if best:
        return best

    # Fallback: closest to 60 DTE regardless of window
    candidates = [(abs(_compute_dte(e) - target), e) for e in expirations
                  if _compute_dte(e) > 20]
    return min(candidates)[1] if candidates else (expirations[-1] if expirations else None)


# ─────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────

def get_expirations(symbol: str, session=None) -> list[str]:
    """
    Return sorted list of available option expiration dates for a symbol.

    Strategy: generate the next 16 weekly Fridays, then probe each with a
    1-row fetch to confirm chain data exists. Works on all plan tiers and
    reliably discovers expirations well beyond the current week.
    """
    today = date.today()
    days_to_friday = (4 - today.weekday()) % 7
    first_friday   = today + timedelta(days=days_to_friday if days_to_friday else 7)

    candidates = [
        (first_friday + timedelta(weeks=i)).isoformat()
        for i in range(16)
    ]

    available = []
    for exp in candidates:
        try:
            payload = _get(
                f"/v3/snapshot/options/{symbol.upper()}",
                params={"expiration_date": exp, "contract_type": "call", "limit": 1},
                session=session,
            )
            if payload.get("results"):
                available.append(exp)
                time.sleep(0.2)
        except MassiveAPIError:
            continue

    return available


def get_spot_price(symbol: str, session=None) -> float:
    """
    Return the current spot price for the underlying.

    Uses /v2/aggs/ticker/{symbol}/prev (previous session close).
    Available on all plan tiers.
    """
    payload = _get(
        f"/v2/aggs/ticker/{symbol.upper()}/prev",
        session=session,
    )

    results = payload.get("results") or []
    if results:
        bar = results[0]
        for key in ("c", "o"):   # close, then open
            val = _safe_float(bar.get(key))
            if val and val > 0:
                return val

    raise MassiveAPIError(
        f"Could not extract spot price for {symbol} from Massive response."
    )


def get_option_chain(
    symbol: str,
    expiration: str,
    session=None,
) -> list[dict]:
    """
    Return normalized option chain rows for one symbol + expiration.

    Fetches all pages automatically.
    Filters to the requested expiration date server-side.

    Each returned row matches the shared option_row schema exactly.
    Missing Greeks are preserved as None (not fabricated).
    """
    raw_results = _get_paginated(
        f"/v3/snapshot/options/{symbol.upper()}",
        params={
            "expiration_date": expiration,
            "limit":           PAGE_LIMIT,
        },
        session=session,
    )

    rows = []
    for raw in raw_results:
        try:
            row = _normalize_result(raw, symbol)
            if row and row["strike"] > 0:
                rows.append(row)
        except Exception:
            continue   # skip malformed rows, never crash the chain

    return rows


# ─────────────────────────────────────────────
# ATM EXTRACTION HELPERS
# (used by main.py to enrich market context)
# ─────────────────────────────────────────────

def extract_atm_straddle(
    chain: list[dict],
    spot: float,
    dte: int,
) -> dict:
    """Extract ATM call and put mid prices for expected move computation."""
    target = [r for r in chain if r["dte"] == dte]

    def nearest(opt_type: str) -> Optional[float]:
        rows = [r for r in target if r["option_type"] == opt_type]
        if not rows:
            return None
        row = min(rows, key=lambda r: abs(r["strike"] - spot))
        return row["mid"] if row["mid"] > 0 else None

    return {
        "atm_call_mid": nearest("call"),
        "atm_put_mid":  nearest("put"),
    }


def extract_front_iv(chain: list[dict], dte: int) -> Optional[float]:
    """ATM call IV for term structure computation."""
    rows = [r for r in chain if r["dte"] == dte
            and r["option_type"] == "call" and r.get("iv")]
    if not rows:
        return None
    rows.sort(key=lambda r: r["strike"])
    return rows[len(rows) // 2]["iv"]


def extract_skew_25d(chain: list[dict], dte: int) -> dict:
    """Approximate 25-delta put/call IVs from the live chain."""
    rows = [r for r in chain if r["dte"] == dte and r.get("delta") is not None]

    def closest_25d(opt_type: str) -> Optional[float]:
        candidates = [r for r in rows if r["option_type"] == opt_type and r.get("iv")]
        if not candidates:
            return None
        return min(candidates, key=lambda r: abs(abs(r["delta"]) - 0.25))["iv"]

    return {
        "put_25d_iv":  closest_25d("put"),
        "call_25d_iv": closest_25d("call"),
    }
