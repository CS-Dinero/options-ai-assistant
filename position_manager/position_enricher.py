"""
position_manager/position_enricher.py
Enriches logged position rows with current market data.

enrich_position_with_live_data(row, provider) → row with:
  current_long_mid, current_short_mid, current_spread_value,
  proposed_roll_credit (estimated), current_delta

Used by the Positions tab to give harvest_engine real numbers
instead of zeros when a position was manually logged without marks.

Falls back cleanly if provider is unavailable — original row unchanged.
"""
from __future__ import annotations

from typing import Any


def _sf(v: Any, d: float = 0.0) -> float:
    try:
        return float(v) if v not in (None, "", "—") else d
    except (TypeError, ValueError):
        return d


def _find_row(chain: list[dict], strike: float, option_type: str) -> dict | None:
    """Find the chain row closest to the target strike."""
    rows = [r for r in chain
            if str(r.get("option_type","")).lower() == option_type.lower()
            and r.get("mid") is not None]
    if not rows:
        return None
    return min(rows, key=lambda r: abs(_sf(r.get("strike")) - strike))


def enrich_position_with_live_data(
    row:      dict[str, Any],
    provider,                    # MarketDataProvider instance
) -> dict[str, Any]:
    """
    Fetch current chain data for the position's symbol and inject
    current_long_mid, current_short_mid, proposed_roll_credit into the row.

    Returns the original row unchanged if enrichment fails.
    """
    import math

    enriched = dict(row)

    try:
        sym          = str(row.get("symbol", "")).upper()
        short_exp    = str(row.get("short_expiration", ""))
        long_exp     = str(row.get("long_expiration", ""))
        short_strike = _sf(row.get("short_strike"))
        long_strike  = _sf(row.get("long_strike"))
        opt_type     = str(row.get("option_side", row.get("option_type","call"))).lower()
        contracts    = max(1, int(_sf(row.get("contracts", 1))))

        if not sym or not short_exp:
            return enriched

        # Fetch spot
        spot = 0.0
        try:
            spot = _sf(provider.get_market(sym).get("spot_price"))
        except Exception:
            pass

        if spot > 0:
            enriched["live_spot"] = spot

        # Fetch short leg chain
        short_chain = []
        try:
            short_chain = provider.get_chain(sym)
            # Filter to short expiration
            short_chain = [r for r in short_chain
                           if str(r.get("expiration","")) == short_exp]
        except Exception:
            pass

        # Fetch long leg chain (may be same as short for calendar)
        long_chain = short_chain
        if long_exp and long_exp != short_exp:
            try:
                long_chain = [r for r in provider.get_chain(sym)
                              if str(r.get("expiration","")) == long_exp]
            except Exception:
                long_chain = []

        # Get current mids
        short_row = _find_row(short_chain, short_strike, opt_type) if short_chain else None
        long_row  = _find_row(long_chain,  long_strike,  opt_type) if long_chain else None

        short_mid = _sf(short_row.get("mid")) if short_row else 0.0
        long_mid  = _sf(long_row.get("mid"))  if long_row  else 0.0

        if short_mid > 0:
            enriched["current_short_mid"] = short_mid
            enriched["mark"]              = short_mid  # for assignment_monitor

        if long_mid > 0:
            enriched["current_long_mid"]  = long_mid
            enriched["current_value"]     = long_mid   # for net_liq calculation

        # Current spread value = long - short (for calendar/diagonal)
        if long_mid > 0 and short_mid > 0:
            spread_val = long_mid - short_mid
            enriched["current_spread_value"] = round(spread_val, 4)

        # Delta from current chain
        if short_row and short_row.get("delta") is not None:
            enriched["short_leg_delta"] = abs(_sf(short_row.get("delta")))
            enriched["short_delta"]     = enriched["short_leg_delta"]
        if long_row and long_row.get("delta") is not None:
            enriched["long_delta"] = abs(_sf(long_row.get("delta")))

        # Estimate proposed_roll_credit using time-value scaling
        # Roll credit ≈ current short mid (close) minus a new short at target DTE
        # Rough estimate: new short ~ current short * sqrt(target_dte / current_dte)
        short_dte = max(int(_sf(row.get("short_dte"), 1)), 1)
        target_dte = 7
        if short_mid > 0:
            new_short_est = short_mid * math.sqrt(target_dte / short_dte)
            roll_credit   = round(new_short_est - short_mid, 4)
            if not enriched.get("proposed_roll_credit"):
                enriched["estimated_new_credit"]     = round(new_short_est, 4)
                enriched["current_spread_cost"]      = short_mid
                enriched["proposed_roll_credit"]     = max(roll_credit, 0.0)

    except Exception:
        pass  # always return original row on any failure

    return enriched


def enrich_snapshot_with_live_data(
    snapshot: dict[str, Any],
    provider,
) -> dict[str, Any]:
    """
    Enrich all positions in a tracker snapshot with live market data.
    Processes calendar_diagonal, credit_spreads, and debit_spreads buckets.
    Returns updated snapshot dict.
    """
    updated = dict(snapshot)
    for bucket in ("calendar_diagonal", "credit_spreads", "debit_spreads", "other"):
        rows = snapshot.get(bucket, [])
        if rows:
            updated[bucket] = [enrich_position_with_live_data(r, provider) for r in rows]
    return updated
