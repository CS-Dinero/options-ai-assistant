"""scanner/xsp_credit_spread_scanner.py — XSP credit spread scanner (bull put + bear call)."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence
from strategies.xsp_credit_spread_builder import XSPCreditSpreadCandidate, build_xsp_credit_spread

@dataclass(slots=True)
class XSPCreditSpreadScannerConfig:
    short_dte_min: int   = 5
    short_dte_max: int   = 10
    short_delta_min: float = 0.20
    short_delta_max: float = 0.30
    spread_widths: tuple  = (1.0, 2.0)
    min_credit: float    = 0.30
    min_credit_width_ratio: float = 0.35
    min_open_interest: int = 200
    max_bid_ask_width: float = 0.10

def _ba_width(q) -> float:
    return float(q.ask) - float(q.bid)

def _liq_score(short_leg, long_leg, cfg: XSPCreditSpreadScannerConfig) -> float:
    oi   = min(100.0, (getattr(short_leg, "open_interest", 0) or 0) / 500 * 100)
    pen  = (_ba_width(short_leg) + _ba_width(long_leg)) * 200
    return max(0.0, min(100.0, oi - pen))

def _valid_short(q, ot: str, cfg: XSPCreditSpreadScannerConfig) -> bool:
    if q.option_type.upper() != ot.upper(): return False
    if q.delta is None: return False
    d = abs(float(q.delta))
    if not (cfg.short_delta_min <= d <= cfg.short_delta_max): return False
    dte = getattr(q, "dte", None)
    if dte is not None and not (cfg.short_dte_min <= int(dte) <= cfg.short_dte_max): return False
    if (getattr(q, "open_interest", 0) or 0) < cfg.min_open_interest: return False
    if _ba_width(q) > cfg.max_bid_ask_width + 1e-9: return False
    return True

def scan_xsp_credit_spreads(
    ticker: str,
    option_type: str,
    quotes: Sequence,
    regime_alignment_score: float,
    cfg: XSPCreditSpreadScannerConfig | None = None,
) -> list[XSPCreditSpreadCandidate]:
    cfg = cfg or XSPCreditSpreadScannerConfig()
    ot  = option_type.upper()
    candidates: list[XSPCreditSpreadCandidate] = []

    shorts = [q for q in quotes if _valid_short(q, ot, cfg)]

    for short_leg in shorts:
        for target_width in cfg.spread_widths:
            short_strike = float(short_leg.strike)
            long_strike  = short_strike - target_width if ot == "PUT" else short_strike + target_width

            long_matches = [
                q for q in quotes
                if q.option_type.upper() == ot
                and abs(float(q.strike) - long_strike) < 0.01
                and (getattr(q, "open_interest", 0) or 0) >= cfg.min_open_interest
                and _ba_width(q) <= cfg.max_bid_ask_width + 1e-9
            ]
            if not long_matches:
                continue
            long_leg = long_matches[0]

            credit = float(short_leg.mid) - float(long_leg.mid)
            if credit < cfg.min_credit:
                continue
            width = abs(short_strike - float(long_leg.strike))
            if width <= 0 or (credit / width) < cfg.min_credit_width_ratio:
                continue

            liq = _liq_score(short_leg, long_leg, cfg)
            c   = build_xsp_credit_spread(ticker, ot, short_leg, long_leg, liq, regime_alignment_score)
            if c is not None:
                candidates.append(c)

    candidates.sort(key=lambda x: x.candidate_score, reverse=True)
    return candidates
