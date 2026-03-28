"""
data_sources/tradier_api.py
Tradier API adapter — options chain, spot price, expirations.

Environment variables required:
    TRADIER_TOKEN    — Bearer token from developer.tradier.com
    TRADIER_BASE_URL — defaults to sandbox; set to production when ready

Sandbox:    https://sandbox.tradier.com/v1   (free, no funded account needed)
Production: https://api.tradier.com/v1       (requires funded Tradier brokerage)

Rate limits:
    Sandbox:    60 req/min
    Production: 120 req/min

Greek/IV data is included in chain responses courtesy of ORATS.
All fields are treated as nullable — scorer normalization handles missing data.
"""

import os
from datetime import date, datetime
from typing import Any, Optional

try:
    import requests
    _REQUESTS_AVAILABLE = True
except ImportError:
    _REQUESTS_AVAILABLE = False

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

TRADIER_TOKEN    = os.getenv("TRADIER_TOKEN", "")
# Default to production. Add TRADIER_BASE_URL = "https://sandbox.tradier.com/v1" to secrets for sandbox.
TRADIER_BASE_URL = os.getenv("TRADIER_BASE_URL", "https://api.tradier.com/v1")

def _load_tradier_from_streamlit_secrets():
    global TRADIER_TOKEN, TRADIER_BASE_URL
    if not TRADIER_TOKEN:
        try:
            import streamlit as st
            # Accept both key names — TRADIER_API_KEY is what Streamlit Cloud UI saves
            TRADIER_TOKEN = (
                st.secrets.get("TRADIER_TOKEN", "")
                or st.secrets.get("TRADIER_API_KEY", "")
            )
            TRADIER_BASE_URL = st.secrets.get("TRADIER_BASE_URL", TRADIER_BASE_URL)
        except Exception:
            pass

_load_tradier_from_streamlit_secrets()

# DTE window for selecting the "long" expiration leg
LONG_DTE_MIN = 45
LONG_DTE_MAX = 75


# ─────────────────────────────────────────────
# CUSTOM EXCEPTIONS
# ─────────────────────────────────────────────

class TradierAPIError(Exception):
    """Raised for auth failures, HTTP errors, or malformed responses."""
    pass


class TradierDataError(Exception):
    """Raised when a response parses cleanly but contains no usable data."""
    pass


# ─────────────────────────────────────────────
# INTERNAL HTTP HELPERS
# ─────────────────────────────────────────────

def _headers() -> dict:
    if not TRADIER_TOKEN:
        raise TradierAPIError(
            "TRADIER_TOKEN environment variable is not set. "
            "Register at developer.tradier.com and export the token."
        )
    return {
        "Authorization": f"Bearer {TRADIER_TOKEN}",
        "Accept":        "application/json",
    }


def _get(path: str, params: Optional[dict] = None, session=None) -> dict:
    """
    Execute a GET request against the Tradier API.

    Args:
        path    — endpoint path e.g. "/markets/quotes"
        params  — query parameters
        session — optional requests.Session for connection pooling / mocking

    Returns:
        Parsed JSON dict.

    Raises:
        TradierAPIError on HTTP 4xx/5xx or network failure.
    """
    if not _REQUESTS_AVAILABLE:
        raise TradierAPIError(
            "'requests' package not installed. Run: pip install requests"
        )

    client = session or requests
    url    = f"{TRADIER_BASE_URL}{path}"

    try:
        resp = client.get(url, headers=_headers(), params=params, timeout=20)
    except Exception as exc:
        raise TradierAPIError(f"Network error reaching Tradier: {exc}") from exc

    if resp.status_code >= 400:
        raise TradierAPIError(
            f"Tradier HTTP {resp.status_code} on {path}: {resp.text[:300]}"
        )

    try:
        return resp.json()
    except Exception as exc:
        raise TradierAPIError(f"Non-JSON response from Tradier: {exc}") from exc


# ─────────────────────────────────────────────
# TYPE-SAFE FIELD PARSERS
# ─────────────────────────────────────────────

def _safe_float(value: Any) -> Optional[float]:
    """Convert to float or return None — never raise."""
    try:
        if value in (None, "", "null", "N/A"):
            return None
        f = float(value)
        # Reject implausible sentinel values
        if f == 0.0:
            return None
        return f
    except (TypeError, ValueError):
        return None


def _safe_float_zero(value: Any) -> float:
    """Convert to float with 0.0 fallback — for bid/ask where 0 is valid."""
    try:
        if value in (None, "", "null", "N/A"):
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _safe_int(value: Any) -> int:
    """Convert to int with 0 fallback — for OI and volume."""
    try:
        if value in (None, "", "null", "N/A"):
            return 0
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _compute_mid(
    bid: float,
    ask: float,
    last: Optional[float] = None,
) -> float:
    """
    Compute mid price with robust fallback chain:
      1. (bid + ask) / 2 if both > 0
      2. last traded price
      3. bid alone
      4. ask alone
      5. 0.0
    """
    if bid > 0 and ask > 0:
        return round((bid + ask) / 2.0, 4)
    if last is not None and last > 0:
        return round(last, 4)
    if bid > 0:
        return round(bid, 4)
    if ask > 0:
        return round(ask, 4)
    return 0.0


def _compute_dte(expiration: str) -> int:
    """Days from today to expiration date. Floored at 0."""
    try:
        exp = datetime.strptime(expiration, "%Y-%m-%d").date()
        return max(0, (exp - date.today()).days)
    except ValueError:
        return 0


# ─────────────────────────────────────────────
# EXPIRATION HELPERS
# ─────────────────────────────────────────────

def pick_short_expiration(expirations: list[str]) -> Optional[str]:
    """
    Choose the nearest expiration >= 5 DTE.
    Avoids same-day or next-day expirations that have no meaningful theta.
    """
    for exp in sorted(expirations):
        dte = _compute_dte(exp)
        if dte >= 5:
            return exp
    return expirations[0] if expirations else None


def pick_long_expiration(expirations: list[str]) -> Optional[str]:
    """
    Choose the expiration closest to the center of the 45–75 DTE window.
    Falls back to whatever is furthest out if no expiration fits the window.
    """
    target_dte   = (LONG_DTE_MIN + LONG_DTE_MAX) // 2   # 60 DTE ideal
    best         = None
    best_dist    = float("inf")

    for exp in expirations:
        dte  = _compute_dte(exp)
        dist = abs(dte - target_dte)
        if LONG_DTE_MIN <= dte <= LONG_DTE_MAX and dist < best_dist:
            best      = exp
            best_dist = dist

    if best:
        return best

    # Fallback: take the expiration with DTE closest to target_dte overall
    for exp in sorted(expirations, key=lambda e: abs(_compute_dte(e) - target_dte)):
        if _compute_dte(exp) > 20:
            return exp

    return expirations[-1] if expirations else None


# ─────────────────────────────────────────────
# ROW NORMALIZER
# ─────────────────────────────────────────────

def _normalize_option_row(
    raw: dict,
    symbol: str,
    expiration: str,
) -> dict:
    """
    Normalize a single Tradier chain row into the shared option_row schema.

    Tradier places Greeks either at top level or nested under a "greeks" key.
    Both locations are checked with top-level as fallback.

    Greek fields are kept as None when missing — the scorer handles this
    via proportional weight redistribution.
    """
    bid  = _safe_float_zero(raw.get("bid"))
    ask  = _safe_float_zero(raw.get("ask"))
    last = _safe_float(raw.get("last"))

    option_type = str(raw.get("option_type", "")).strip().lower()
    if option_type not in ("call", "put"):
        # Tradier sometimes uses "C"/"P"
        raw_type = str(raw.get("option_type", ""))
        option_type = "call" if raw_type.upper().startswith("C") else "put"

    # Greeks: prefer nested "greeks" dict, fall back to top-level fields
    greeks = raw.get("greeks") or {}

    def _greek(nested_key: str, top_key: str) -> Optional[float]:
        return _safe_float(greeks.get(nested_key)) or _safe_float(raw.get(top_key))

    delta = _greek("delta",   "delta")
    gamma = _greek("gamma",   "gamma")
    theta = _greek("theta",   "theta")
    vega  = _greek("vega",    "vega")
    # Tradier/ORATS uses "mid_iv" for the mid-market IV
    iv_raw = greeks.get("mid_iv") or greeks.get("smv_vol") or raw.get("iv")
    iv     = _safe_float(iv_raw)
    if iv is not None:
        iv = round(iv * 100, 4)  # convert decimal to percentage (0.16 → 16.0)

    return {
        "symbol":        symbol.upper(),
        "expiration":    expiration,
        "dte":           _compute_dte(expiration),
        "option_type":   option_type,
        "strike":        float(raw.get("strike", 0)),
        "bid":           bid,
        "ask":           ask,
        "mid":           _compute_mid(bid, ask, last),
        "delta":         delta,
        "gamma":         gamma,
        "theta":         theta,
        "vega":          vega,
        "iv":            iv,
        "open_interest": _safe_int(raw.get("open_interest")),
        "volume":        _safe_int(raw.get("volume")),
    }


# ─────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────

def get_expirations(symbol: str, session=None) -> list[str]:
    """
    Return sorted list of available option expiration dates (ISO format).

    Tradier endpoint: GET /markets/options/expirations
    Params: symbol, includeAllRoots=true, strikes=false

    Returns [] if no expirations found (e.g. non-optionable symbol).
    Raises TradierAPIError on auth/network failure.
    """
    payload = _get(
        "/markets/options/expirations",
        params={
            "symbol":          symbol.upper(),
            "includeAllRoots": "true",
            "strikes":         "false",
        },
        session=session,
    )

    # Tradier response shape:
    # {"expirations": {"date": ["2026-03-21", "2026-03-28", ...]}}
    # or {"expirations": null} when none available
    expirations_block = payload.get("expirations")
    if not expirations_block:
        return []

    dates = expirations_block.get("date", [])

    # Normalize: Tradier returns a single string when only one date exists
    if isinstance(dates, str):
        dates = [dates]

    return sorted(set(dates))


def get_spot_price(symbol: str, session=None) -> float:
    """
    Return the current spot price for a symbol.

    Tradier endpoint: GET /markets/quotes
    Fallback chain: last → close → bid/ask midpoint

    Raises TradierAPIError if no usable price is found.
    """
    payload = _get(
        "/markets/quotes",
        params={"symbols": symbol.upper(), "greeks": "false"},
        session=session,
    )

    # Tradier response shape:
    # {"quotes": {"quote": {...}}}  (single symbol)
    # {"quotes": {"quote": [{...}, ...]}}  (multiple symbols)
    quotes_block = payload.get("quotes", {})
    quote        = quotes_block.get("quote")

    if isinstance(quote, list):
        quote = next((q for q in quote if q.get("symbol", "").upper() == symbol.upper()), None)

    if not quote:
        raise TradierAPIError(f"No quote data returned for {symbol}")

    # Fallback chain for price
    for key in ("last", "close"):
        val = _safe_float(quote.get(key))
        if val and val > 0:
            return val

    bid = _safe_float_zero(quote.get("bid"))
    ask = _safe_float_zero(quote.get("ask"))
    mid = _compute_mid(bid, ask)
    if mid > 0:
        return mid

    raise TradierAPIError(
        f"Could not extract spot price for {symbol} — "
        f"quote fields: {list(quote.keys())}"
    )


def get_option_chain(
    symbol: str,
    expiration: str,
    session=None,
) -> list[dict]:
    """
    Return normalized option chain rows for one symbol + expiration.

    Tradier endpoint: GET /markets/options/chains
    Params: symbol, expiration, greeks=true

    Returns [] if Tradier has no chain data for this expiration.
    Raises TradierAPIError on auth/network failure.

    Each returned row matches the shared option_row schema exactly.
    Missing Greeks are preserved as None (not fabricated).
    """
    payload = _get(
        "/markets/options/chains",
        params={
            "symbol":     symbol.upper(),
            "expiration": expiration,
            "greeks":     "true",
        },
        session=session,
    )

    # Tradier response shape:
    # {"options": {"option": [{...}, ...]}}
    # or {"options": null} when no chain data
    options_block = payload.get("options")
    if not options_block:
        return []

    raw_options = options_block.get("option", [])

    # Normalize: single option returned as dict not list
    if isinstance(raw_options, dict):
        raw_options = [raw_options]

    if not raw_options:
        return []

    rows = []
    for raw in raw_options:
        try:
            row = _normalize_option_row(raw, symbol, expiration)
            # Basic sanity: reject rows with no usable strike
            if row["strike"] > 0:
                rows.append(row)
        except Exception:
            # Skip malformed rows — don't crash the whole chain
            continue

    return rows


# ─────────────────────────────────────────────
# ATM EXTRACTION HELPERS
# (used by main.py to update market context from live chain)
# ─────────────────────────────────────────────

def extract_atm_straddle(
    chain: list[dict],
    spot: float,
    dte: int,
) -> dict:
    """
    Find ATM call and put mid prices from the chain for EM computation.
    Matches rows closest to spot with the given DTE.

    Returns:
        {"atm_call_mid": float|None, "atm_put_mid": float|None}
    """
    target_rows = [r for r in chain if r["dte"] == dte]
    if not target_rows:
        return {"atm_call_mid": None, "atm_put_mid": None}

    def nearest(opt_type: str) -> Optional[float]:
        rows = [r for r in target_rows if r["option_type"] == opt_type]
        if not rows:
            return None
        row = min(rows, key=lambda r: abs(r["strike"] - spot))
        return row["mid"] if row["mid"] > 0 else None

    return {
        "atm_call_mid": nearest("call"),
        "atm_put_mid":  nearest("put"),
    }


def extract_front_iv(chain: list[dict], dte: int) -> Optional[float]:
    """
    Estimate front-month IV from the ATM call's IV field.
    Returns None if unavailable (scorer will handle gracefully).
    """
    rows = [r for r in chain if r["dte"] == dte and r["option_type"] == "call" and r["iv"]]
    if not rows:
        return None
    # Use median-ish: sort by strike, pick the middle row's IV
    rows.sort(key=lambda r: r["strike"])
    mid_row = rows[len(rows) // 2]
    return mid_row["iv"]


def extract_skew_25d(chain: list[dict], dte: int) -> dict:
    """
    Approximate 25-delta put and call IVs from the live chain.
    Finds the option whose |delta| is closest to 0.25.

    Returns:
        {"put_25d_iv": float|None, "call_25d_iv": float|None}
    """
    rows = [r for r in chain if r["dte"] == dte and r.get("delta") is not None]

    def closest_25d(opt_type: str) -> Optional[float]:
        candidates = [r for r in rows if r["option_type"] == opt_type and r["iv"]]
        if not candidates:
            return None
        best = min(candidates, key=lambda r: abs(abs(r["delta"]) - 0.25))
        return best["iv"]

    return {
        "put_25d_iv":  closest_25d("put"),
        "call_25d_iv": closest_25d("call"),
    }
