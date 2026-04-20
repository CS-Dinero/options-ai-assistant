"""strategies/xsp_credit_spread_builder.py — XSP bull put / bear call credit spread builder."""
from __future__ import annotations
from dataclasses import dataclass, field

@dataclass(slots=True)
class XSPCreditSpreadCandidate:
    ticker: str
    structure: str          # BULL_PUT_SPREAD | BEAR_CALL_SPREAD
    option_type: str        # PUT | CALL
    short_strike: float
    long_strike: float
    expiry: str
    short_dte: int
    short_delta: float
    long_delta: float
    short_mid: float
    long_mid: float
    credit: float
    width: float
    max_loss: float
    credit_width_ratio: float
    liquidity_score: float
    candidate_score: float
    notes: list[str] = field(default_factory=list)

def build_xsp_credit_spread(
    ticker: str,
    option_type: str,
    short_leg,
    long_leg,
    liquidity_score: float,
    regime_alignment_score: float,
) -> XSPCreditSpreadCandidate | None:
    ot = option_type.upper()
    structure = "BULL_PUT_SPREAD" if ot == "PUT" else "BEAR_CALL_SPREAD"

    short_mid = float(short_leg.mid)
    long_mid  = float(long_leg.mid)
    credit    = round(short_mid - long_mid, 4)
    if credit <= 0:
        return None

    width     = round(abs(float(short_leg.strike) - float(long_leg.strike)), 4)
    max_loss  = round((width - credit) * 100, 2)
    cwr       = round(credit / max(0.01, width), 4)

    # Score: credit richness + liquidity + regime alignment
    credit_score = min(100.0, (credit / max(0.01, width)) * 100 * 2)
    candidate_score = round(
        credit_score      * 0.35
        + liquidity_score * 0.35
        + regime_alignment_score * 0.30,
        2,
    )

    return XSPCreditSpreadCandidate(
        ticker=ticker,
        structure=structure,
        option_type=ot,
        short_strike=float(short_leg.strike),
        long_strike=float(long_leg.strike),
        expiry=str(short_leg.expiry),
        short_dte=int(getattr(short_leg, "dte", 0)),
        short_delta=round(abs(float(short_leg.delta or 0)), 4),
        long_delta=round(abs(float(long_leg.delta or 0)), 4),
        short_mid=round(short_mid, 4),
        long_mid=round(long_mid, 4),
        credit=credit,
        width=width,
        max_loss=max_loss,
        credit_width_ratio=cwr,
        liquidity_score=round(liquidity_score, 2),
        candidate_score=candidate_score,
        notes=[f"credit={credit:.2f}", f"cwr={cwr:.2f}", f"liq={liquidity_score:.1f}"],
    )
