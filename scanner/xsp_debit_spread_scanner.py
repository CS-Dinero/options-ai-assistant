"""scanner/xsp_debit_spread_scanner.py — XSP debit spread scanner (bull call + bear put)."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence
from strategies.xsp_debit_spread_builder import XSPDebitSpreadCandidate, build_xsp_debit_spread

@dataclass(slots=True)
class XSPDebitSpreadScannerConfig:
    dte_min: int   = 7
    dte_max: int   = 21
    long_delta_min: float = 0.45
    long_delta_max: float = 0.70
    spread_widths: tuple  = (1.0, 2.0)
    min_debit: float  = 0.20
    max_debit: float  = 0.75
    min_reward_risk: float = 0.75
    min_open_interest: int = 200
    max_bid_ask_width: float = 0.10

def _ba_width(q) -> float:
    return float(q.ask) - float(q.bid)

def _liq_score(long_leg, short_leg) -> float:
    oi  = min(100.0, (getattr(long_leg, "open_interest", 0) or 0) / 500 * 100)
    pen = (_ba_width(long_leg) + _ba_width(short_leg)) * 200
    return max(0.0, min(100.0, oi - pen))

def _valid_long(q, ot: str, cfg: XSPDebitSpreadScannerConfig) -> bool:
    if q.option_type.upper() != ot.upper(): return False
    if q.delta is None: return False
    d = abs(float(q.delta))
    if not (cfg.long_delta_min <= d <= cfg.long_delta_max): return False
    dte = getattr(q, "dte", None)
    if dte is not None and not (cfg.dte_min <= int(dte) <= cfg.dte_max): return False
    if (getattr(q, "open_interest", 0) or 0) < cfg.min_open_interest: return False
    if _ba_width(q) > cfg.max_bid_ask_width + 1e-9: return False
    return True

def scan_xsp_debit_spreads(
    ticker: str,
    option_type: str,
    quotes: Sequence,
    regime_alignment_score: float,
    cfg: XSPDebitSpreadScannerConfig | None = None,
) -> list[XSPDebitSpreadCandidate]:
    cfg = cfg or XSPDebitSpreadScannerConfig()
    ot  = option_type.upper()
    candidates: list[XSPDebitSpreadCandidate] = []

    longs = [q for q in quotes if _valid_long(q, ot, cfg)]

    for long_leg in longs:
        for target_width in cfg.spread_widths:
            long_strike  = float(long_leg.strike)
            short_strike = long_strike + target_width if ot == "CALL" else long_strike - target_width

            short_matches = [
                q for q in quotes
                if q.option_type.upper() == ot
                and abs(float(q.strike) - short_strike) < 0.01
                and (getattr(q, "open_interest", 0) or 0) >= cfg.min_open_interest
                and _ba_width(q) <= cfg.max_bid_ask_width + 1e-9
            ]
            if not short_matches:
                continue
            short_leg = short_matches[0]

            debit = float(long_leg.mid) - float(short_leg.mid)
            if not (cfg.min_debit <= debit <= cfg.max_debit):
                continue
            width = abs(long_strike - short_strike)
            max_profit = (width - debit) * 100
            max_loss   = debit * 100
            rr = max_profit / max(0.01, max_loss)
            if rr < cfg.min_reward_risk:
                continue

            liq = _liq_score(long_leg, short_leg)
            c   = build_xsp_debit_spread(ticker, ot, long_leg, short_leg, liq, regime_alignment_score)
            if c is not None:
                candidates.append(c)

    candidates.sort(key=lambda x: x.candidate_score, reverse=True)
    return candidates
