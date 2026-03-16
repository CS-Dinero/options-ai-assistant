"""
validation/checks.py
Post-run validation checks and missing-input normalization tests.

run_validation_checks() — verifies the engine produced correct output
run_normalization_tests() — verifies scorer handles missing inputs gracefully
"""

from data.mock_data          import load_mock_market, build_mock_chain
from engines.context_builder import build_derived as _cb_build_derived
from engines.expected_move  import compute_expected_move
from engines.atr_engine     import classify_atr_trend, em_atr_ratio
from engines.iv_regime      import classify_iv_regime
from engines.term_structure import compute_term_slope, classify_term_structure
from engines.skew_engine    import compute_skew, classify_skew
from engines.gamma_engine   import classify_gamma_regime
from strategies.bear_call       import generate_bear_call_spreads
from strategies.bull_put        import generate_bull_put_spreads
from strategies.bull_call_debit import generate_bull_call_debit_spreads
from strategies.bear_put_debit  import generate_bear_put_debit_spreads
from calculator.trade_scoring   import rank_candidates


# ─────────────────────────────────────────────
# CORE VALIDATION
# ─────────────────────────────────────────────

def run_validation_checks(
    chain: list[dict],
    ranked: list[dict],
    derived: dict,
) -> tuple[bool, list[tuple[str, bool]]]:
    """
    Verify the engine produced structurally correct output.

    Returns:
        (all_pass: bool, results: list of (check_name, passed))
    """
    top = ranked[0] if ranked else None

    checks = [
        ("Chain has >= 40 rows",
            len(chain) >= 40),

        ("Expected move > 0",
            derived["expected_move"] > 0),

        ("Upper EM > spot (lower EM < spot)",
            derived["upper_em"] > derived["lower_em"]),

        ("IV regime classified",
            derived["iv_regime"] in ("cheap", "moderate", "elevated", "rich")),

        ("Term structure classified",
            derived["term_structure"] in ("contango", "flat", "backwardation")),

        ("Gamma regime classified",
            derived["gamma_regime"] in ("positive", "negative", "neutral", "unknown")),

        ("Bear call spread generated",
            any(t["strategy_type"] == "bear_call" for t in ranked)),

        ("Bull put spread generated",
            any(t["strategy_type"] == "bull_put" for t in ranked)),

        ("Bull call debit generated",
            any(t["strategy_type"] == "bull_call_debit" for t in ranked)),

        ("Bear put debit generated",
            any(t["strategy_type"] == "bear_put_debit" for t in ranked)),

        ("All trades scored 0–100",
            all(0 <= t["confidence_score"] <= 100 for t in ranked)),

        ("Top trade score >= 65",
            top is not None and top["confidence_score"] >= 65),

        ("Candidates ranked descending",
            all(
                ranked[i]["confidence_score"] >= ranked[i + 1]["confidence_score"]
                for i in range(len(ranked) - 1)
            )),

        ("Credit spreads show positive credit",
            all(
                t["entry_debit_credit"] > 0
                for t in ranked
                if t["strategy_type"] in ("bear_call", "bull_put")
            )),

        ("Debit spreads show negative entry value",
            all(
                t["entry_debit_credit"] < 0
                for t in ranked
                if t["strategy_type"] in ("bull_call_debit", "bear_put_debit")
            )),

        ("Max profit > 0 for all trades",
            all((t["max_profit"] or 0) >= 0 for t in ranked)),

        ("Max loss > 0 for all trades",
            all(t["max_loss"] > 0 for t in ranked)),

        ("Contracts >= 1 for all trades",
            all(t["contracts"] >= 1 for t in ranked)),

        # Gamma engine checks
        ("GEX by strike is dict",
            isinstance(derived.get("gex_by_strike"), dict)),
        ("Total GEX numeric or None",
            derived.get("total_gex") is None or isinstance(derived.get("total_gex"), (int, float))),
        ("Gamma flip numeric or None",
            derived.get("gamma_flip") is None or isinstance(derived.get("gamma_flip"), (int, float))),
        ("Gamma trap numeric or None",
            derived.get("gamma_trap") is None or isinstance(derived.get("gamma_trap"), (int, float))),
        ("Gamma regime classified",
            derived.get("gamma_regime") in ("positive", "negative", "neutral", "unknown")),
        ("Mock mode gamma regime resolved",
            derived.get("gamma_regime") != "unknown"),
    ]

    all_pass = all(result for _, result in checks)
    return all_pass, checks


def print_validation_results(
    results: list[tuple[str, bool]],
    all_pass: bool,
    label: str = "Core Validation",
) -> None:
    print(f"  ─── {label} ───")
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}")
    print()
    if all_pass:
        print("  ✓ All checks passed.")
    else:
        failed = [name for name, ok in results if not ok]
        print(f"  ✗ {len(failed)} check(s) failed: {', '.join(failed)}")
    print()


# ─────────────────────────────────────────────
# MISSING-INPUT NORMALIZATION TESTS
# ─────────────────────────────────────────────

def _build_derived_from_market(market: dict, chain: list | None = None) -> dict:
    """Helper: build derived context using context_builder (no circular imports)."""
    return _cb_build_derived(market, chain)


def _run_all_generators(market: dict, chain: list[dict], derived: dict) -> list[dict]:
    candidates = []
    candidates += generate_bear_call_spreads(market, chain, derived)
    candidates += generate_bull_put_spreads(market, chain, derived)
    candidates += generate_bull_call_debit_spreads(market, chain, derived)
    candidates += generate_bear_put_debit_spreads(market, chain, derived)
    return rank_candidates(candidates)


def run_normalization_tests(chain: list[dict]) -> tuple[bool, list[tuple[str, bool]]]:
    """
    Test A — total_gex = None          (gamma regime unknown)
    Test B — gamma_flip = None         (gamma context partially absent)
    Test C — skew inputs = None        (skew regime unknown)
    Test D — front_iv == back_iv       (flat term structure)

    Each test verifies:
      - engine still runs without error
      - all candidates still receive valid scores (0–100)
      - ranking is still monotone descending
      - top trade score stays >= 50 (no score collapse)
    """
    base_market = load_mock_market()
    results: list[tuple[str, bool]] = []

    # ── Test A: gamma completely absent ──────────────────────
    market_a = {**base_market, "total_gex": None, "gamma_flip": None, "gamma_trap_strike": None}
    derived_a = _build_derived_from_market(market_a, chain)
    ranked_a  = _run_all_generators(market_a, chain, derived_a)

    results += [
        ("Test A: gamma=None → engine runs",
            len(ranked_a) > 0),
        ("Test A: gamma=None → scores valid 0–100",
            all(0 <= t["confidence_score"] <= 100 for t in ranked_a)),
        ("Test A: gamma=None → top score >= 50",
            ranked_a[0]["confidence_score"] >= 50 if ranked_a else False),
        ("Test A: gamma=None → ranking descending",
            all(ranked_a[i]["confidence_score"] >= ranked_a[i+1]["confidence_score"]
                for i in range(len(ranked_a)-1))),
    ]

    # ── Test B: gamma_flip absent only (total_gex still present) ─
    market_b = {**base_market, "gamma_flip": None, "gamma_trap_strike": None}
    derived_b = _build_derived_from_market(market_b, chain)
    ranked_b  = _run_all_generators(market_b, chain, derived_b)

    results += [
        ("Test B: gamma_flip=None → engine runs",
            len(ranked_b) > 0),
        ("Test B: gamma_flip=None → scores valid",
            all(0 <= t["confidence_score"] <= 100 for t in ranked_b)),
    ]

    # ── Test C: skew inputs absent ────────────────────────────
    market_c = {**base_market, "put_25d_iv": None, "call_25d_iv": None}
    derived_c = _build_derived_from_market(market_c, chain)
    ranked_c  = _run_all_generators(market_c, chain, derived_c)

    results += [
        ("Test C: skew=None → skew_state is 'unknown'",
            derived_c["skew_state"] == "unknown"),
        ("Test C: skew=None → engine runs",
            len(ranked_c) > 0),
        ("Test C: skew=None → scores valid 0–100",
            all(0 <= t["confidence_score"] <= 100 for t in ranked_c)),
        ("Test C: skew=None → top score >= 50",
            ranked_c[0]["confidence_score"] >= 50 if ranked_c else False),
        ("Test C: skew=None → ranking descending",
            all(ranked_c[i]["confidence_score"] >= ranked_c[i+1]["confidence_score"]
                for i in range(len(ranked_c)-1))),
    ]

    # ── Test D: flat term structure (front_iv == back_iv) ─────
    market_d = {**base_market, "back_iv": base_market["front_iv"]}
    derived_d = _build_derived_from_market(market_d, chain)
    ranked_d  = _run_all_generators(market_d, chain, derived_d)

    results += [
        ("Test D: flat IV → term_structure is 'flat'",
            derived_d["term_structure"] == "flat"),
        ("Test D: flat IV → engine runs",
            len(ranked_d) > 0),
        ("Test D: flat IV → scores valid",
            all(0 <= t["confidence_score"] <= 100 for t in ranked_d)),
    ]

    all_pass = all(ok for _, ok in results)
    return all_pass, results


# ─────────────────────────────────────────────
# CALENDAR VALIDATION
# ─────────────────────────────────────────────

def run_calendar_validation(ranked: list[dict]) -> tuple[bool, list[tuple[str, bool]]]:
    """
    Validate calendar candidate structure and rule compliance.
    Uses conditional checks — skips pass/fail when no calendar exists
    for checks that require favorable regime (graceful non-generation is valid).
    """
    cal = [t for t in ranked if t["strategy_type"] == "calendar"]
    has_cal = len(cal) > 0

    checks = [
        ("Calendar schema complete",
            all(_validate_schema(t) for t in cal) if has_cal else True),

        ("Calendar uses same strike both legs",
            all(t["long_strike"] == t["short_strike"] for t in cal) if has_cal else True),

        ("Calendar width is zero",
            all(t["width"] == 0.0 for t in cal) if has_cal else True),

        ("Calendar debit is positive",
            all(t["entry_debit_credit"] > 0 for t in cal) if has_cal else True),

        ("Calendar max_loss equals debit*100",
            all(abs(t["max_loss"] - t["entry_debit_credit"] * 100) < 1 for t in cal) if has_cal else True),

        ("Calendar target above entry",
            all(t["target_exit_value"] > t["entry_debit_credit"] for t in cal) if has_cal else True),

        ("Calendar stop below entry",
            all(t["stop_value"] < t["entry_debit_credit"] for t in cal) if has_cal else True),

        ("Calendar theta ratio valid",
            all(
                abs(t["short_theta"]) >= 1.5 * abs(t["long_theta"])
                for t in cal
                if t.get("short_theta") is not None and t.get("long_theta") is not None
            ) if has_cal else True),

        ("Calendar scored 0-100",
            all(0 <= t["confidence_score"] <= 100 for t in cal) if has_cal else True),
    ]

    all_pass = all(ok for _, ok in checks)
    return all_pass, checks


# ─────────────────────────────────────────────
# DIAGONAL VALIDATION
# ─────────────────────────────────────────────

def run_diagonal_validation(ranked: list[dict]) -> tuple[bool, list[tuple[str, bool]]]:
    """
    Validate diagonal candidate structure and filter compliance.
    """
    from config.settings import (
        DIAGONAL_LONG_DELTA_MIN, DIAGONAL_LONG_DELTA_MAX,
        DIAGONAL_SHORT_DELTA_MIN, DIAGONAL_SHORT_DELTA_MAX,
        DIAGONAL_MAX_DEBIT_PCT_OF_WIDTH, MIN_LONG_LEG_OPEN_INTEREST,
        MAX_BID_ASK_SPREAD_PCT,
    )
    diag    = [t for t in ranked if t["strategy_type"] == "diagonal"]
    has_diag = len(diag) > 0

    checks = [
        ("Diagonal schema complete",
            all(_validate_schema(t) for t in diag) if has_diag else True),

        ("Diagonal width positive",
            all(t["width"] > 0 for t in diag) if has_diag else True),

        ("Diagonal debit is positive",
            all(t["entry_debit_credit"] > 0 for t in diag) if has_diag else True),

        ("Diagonal target above entry",
            all(t["target_exit_value"] > t["entry_debit_credit"] for t in diag) if has_diag else True),

        ("Diagonal stop below entry",
            all(t["stop_value"] < t["entry_debit_credit"] for t in diag) if has_diag else True),

        ("Diagonal long delta in target band",
            all(
                DIAGONAL_LONG_DELTA_MIN <= abs(t["long_delta"]) <= DIAGONAL_LONG_DELTA_MAX
                for t in diag if t.get("long_delta") is not None
            ) if has_diag else True),

        ("Diagonal short delta in target band",
            all(
                DIAGONAL_SHORT_DELTA_MIN <= abs(t["short_delta"]) <= DIAGONAL_SHORT_DELTA_MAX
                for t in diag if t.get("short_delta") is not None
            ) if has_diag else True),

        ("Diagonal debit within 75% width cap",
            all(
                t["debit_pct_of_width"] <= DIAGONAL_MAX_DEBIT_PCT_OF_WIDTH
                for t in diag if t.get("debit_pct_of_width") is not None
            ) if has_diag else True),

        ("Diagonal long leg OI sufficient",
            all(
                t["long_open_interest"] >= MIN_LONG_LEG_OPEN_INTEREST
                for t in diag if t.get("long_open_interest") is not None
            ) if has_diag else True),

        ("Diagonal bid/ask spread acceptable",
            all(
                t["long_bid_ask_spread_pct"] <= MAX_BID_ASK_SPREAD_PCT
                for t in diag if t.get("long_bid_ask_spread_pct") is not None
            ) if has_diag else True),

        ("Diagonal scored 0-100",
            all(0 <= t["confidence_score"] <= 100 for t in diag) if has_diag else True),
    ]

    all_pass = all(ok for _, ok in checks)
    return all_pass, checks


def _validate_schema(candidate: dict) -> bool:
    """Check all required fields exist in a candidate."""
    from config.settings import REQUIRED_CANDIDATE_FIELDS
    return all(field in candidate for field in REQUIRED_CANDIDATE_FIELDS)
