"""
adapters/report_adapter.py
Normalizes raw report/market-context dicts from any source into the
v15 engine schema — same field names used by engines/context_builder.py.

Handles alias resolution, regime string normalization, and EM
reconstruction when upper/lower_em are missing.
"""
from __future__ import annotations
from typing import Any


REPORT_ALIASES: dict[str, list[str]] = {
    "symbol":         ["symbol", "ticker", "underlying"],
    "spot_price":     ["spot_price", "spot", "underlying_price", "last", "close"],
    "expected_move":  ["expected_move", "em", "move_expected", "exp_move"],
    "upper_em":       ["upper_em", "em_upper", "upper_expected_move"],
    "lower_em":       ["lower_em", "em_lower", "lower_expected_move"],
    "em_atr_ratio":   ["em_atr_ratio", "expected_move_atr_ratio"],
    "front_iv":       ["front_iv", "iv_front", "iv", "atm_iv"],
    "back_iv":        ["back_iv", "iv_back"],
    "iv_percentile":  ["iv_percentile", "iv_pctile", "ivp", "iv_rank"],
    "term_structure": ["term_structure", "term_regime", "term"],
    "term_slope":     ["term_slope", "term_structure_slope"],
    "skew_state":     ["skew_state", "skew_regime", "skew"],
    "gamma_regime":   ["gamma_regime", "gex_regime", "gamma"],
    "gamma_flip":     ["gamma_flip", "flip", "gex_flip"],
    "gamma_trap":     ["gamma_trap", "trap", "gex_trap"],
    "atr_trend":      ["atr_trend", "atr_state"],
    "atr_14":         ["atr_14", "atr"],
    "atr_prior":      ["atr_prior"],
    "put_25d_iv":     ["put_25d_iv", "put_25d", "skew_put"],
    "call_25d_iv":    ["call_25d_iv", "call_25d", "skew_call"],
}

IV_REGIMES      = {"cheap", "moderate", "elevated", "rich",
                   "low", "normal", "extreme"}
TERM_STRUCTURES = {"contango", "flat", "backwardation"}
GAMMA_REGIMES   = {"positive", "negative", "neutral", "unknown"}


def _find(report: dict[str, Any], aliases: list[str], default: Any = None) -> Any:
    for key in aliases:
        if key in report and report[key] not in (None, ""):
            return report[key]
    return default


def _sf(v: Any, default: float = 0.0) -> float:
    try:
        return float(v) if v not in (None, "") else default
    except (TypeError, ValueError):
        return default


def _norm_regime(v: Any, valid: set[str], default: str) -> str:
    t = str(v or "").strip().lower()
    return t if t in valid else default


def normalize_report(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Normalize any raw report dict to the v15 market dict schema.

    Works with:
    - massive_api.py output (spot_price, front_iv, etc.)
    - EGPE spec report dicts (spot, iv_regime, etc.)
    - Tradier provider output
    - CSV provider output
    """
    spot = _sf(_find(raw, REPORT_ALIASES["spot_price"]))
    em   = _sf(_find(raw, REPORT_ALIASES["expected_move"]))

    upper_em = _sf(_find(raw, REPORT_ALIASES["upper_em"]))
    lower_em = _sf(_find(raw, REPORT_ALIASES["lower_em"]))
    if upper_em <= 0 and spot > 0 and em > 0:
        upper_em = round(spot + em, 4)
    if lower_em <= 0 and spot > 0 and em > 0:
        lower_em = round(spot - em, 4)

    return {
        "symbol":           str(_find(raw, REPORT_ALIASES["symbol"], "")).upper(),
        "spot_price":       spot,
        "expected_move":    em,
        "upper_em":         upper_em,
        "lower_em":         lower_em,
        "em_atr_ratio":     _sf(_find(raw, REPORT_ALIASES["em_atr_ratio"])),
        "front_iv":         _sf(_find(raw, REPORT_ALIASES["front_iv"])),
        "back_iv":          _sf(_find(raw, REPORT_ALIASES["back_iv"])),
        "iv_percentile":    _sf(_find(raw, REPORT_ALIASES["iv_percentile"])),
        "term_structure":   _norm_regime(_find(raw, REPORT_ALIASES["term_structure"]), TERM_STRUCTURES, "flat"),
        "term_slope":       _sf(_find(raw, REPORT_ALIASES["term_slope"])),
        "skew_state":       str(_find(raw, REPORT_ALIASES["skew_state"], "unknown")).lower(),
        "gamma_regime":     _norm_regime(_find(raw, REPORT_ALIASES["gamma_regime"]), GAMMA_REGIMES, "neutral"),
        "gamma_flip":       _sf(_find(raw, REPORT_ALIASES["gamma_flip"])) or None,
        "gamma_trap":       _sf(_find(raw, REPORT_ALIASES["gamma_trap"])) or None,
        "atr_trend":        str(_find(raw, REPORT_ALIASES["atr_trend"], "unknown")).lower(),
        "atr_14":           _sf(_find(raw, REPORT_ALIASES["atr_14"])),
        "atr_prior":        _sf(_find(raw, REPORT_ALIASES["atr_prior"])),
        "put_25d_iv":       _sf(_find(raw, REPORT_ALIASES["put_25d_iv"])) or None,
        "call_25d_iv":      _sf(_find(raw, REPORT_ALIASES["call_25d_iv"])) or None,
        # pass through any extra keys (e.g. preferred_risk_dollars, short_dte_target)
        **{k: v for k, v in raw.items()
           if k not in {alias for aliases in REPORT_ALIASES.values() for alias in aliases}},
    }
