"""
engines/portfolio_allocator.py
Multi-symbol portfolio allocation for the Options AI Assistant.

Decides how to split risk across symbols given:
  - account size + per-symbol risk caps
  - which symbols are in "approved" environment
  - VGA alignment across symbols
  - capital already deployed

Phase 1 scope:
  - 2–4 symbols (SPY, QQQ, and optional single-name)
  - Equal-weight risk allocation as default
  - VGA override: only allocate to symbols whose regime allows trading
  - Returns per-symbol risk budget + allocation rationale

Phase 2 (not yet built):
  - Dynamic skew toward premium_selling symbols
  - Cross-symbol correlation adjustments
  - Calendar-first allocation when multiple symbols in pin zone
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class SymbolAllocation:
    symbol:           str
    regime:           str
    vga_environment:  str
    allowed:          bool
    risk_dollars:     float
    size_multiplier:  float
    rationale:        str


@dataclass
class PortfolioAllocation:
    total_risk_budget:  float
    per_symbol:         list[SymbolAllocation]
    active_symbols:     list[str]
    inactive_symbols:   list[str]
    allocation_mode:    str
    notes:              list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def allocate_portfolio(
    symbol_results: list[dict[str, Any]],
    account_size:   float = 200_000,
    max_total_pct:  float = 0.04,    # 4% total risk across all symbols
    max_per_sym_pct:float = 0.02,    # 2% per symbol
    min_risk_dollars: float = 100,
) -> PortfolioAllocation:
    """
    Allocate risk budget across symbols given their engine outputs.

    Parameters
    ----------
    symbol_results:
        List of run_options_engine() output dicts, one per symbol.
    account_size:
        Total account equity.
    max_total_pct:
        Maximum total risk as fraction of account (default 4%).
    max_per_sym_pct:
        Maximum risk per symbol as fraction of account (default 2%).
    min_risk_dollars:
        Minimum allocation to bother trading a symbol.

    Returns
    -------
    PortfolioAllocation with per-symbol budgets and rationale.
    """
    total_budget    = account_size * max_total_pct
    per_sym_cap     = account_size * max_per_sym_pct

    active: list[SymbolAllocation]   = []
    inactive: list[SymbolAllocation] = []
    notes: list[str] = []

    # Score each symbol by regime quality
    scored: list[tuple[float, dict]] = []
    for result in symbol_results:
        sym     = result.get("market", {}).get("symbol", "")
        regime  = result.get("regime", {})
        vga     = result.get("vga", "mixed")
        mult    = float(regime.get("size_multiplier", 1.0))
        name    = regime.get("regime", "mixed")

        # Don't allocate to no_trade or zero-multiplier regimes
        if name == "no_trade" or mult == 0:
            inactive.append(SymbolAllocation(
                symbol=sym, regime=name, vga_environment=vga,
                allowed=False, risk_dollars=0, size_multiplier=0,
                rationale=f"Regime '{name}' — no trade.",
            ))
            continue

        # Score: premium_selling > neutral_time_spreads > cautious > mixed
        quality = {
            "premium_selling":      1.0,
            "neutral_time_spreads": 0.85,
            "cautious_directional": 0.50,
            "trend_directional":    0.60,
            "mixed":                0.40,
        }.get(vga, 0.30)

        scored.append((quality * mult, result))

    if not scored:
        notes.append("No symbols cleared for trading in current regime.")
        return PortfolioAllocation(
            total_risk_budget=0,
            per_symbol=inactive,
            active_symbols=[],
            inactive_symbols=[r.get("market", {}).get("symbol", "") for r in symbol_results],
            allocation_mode="no_trade",
            notes=notes,
        )

    # Sort by score descending, allocate equal weight then cap
    scored.sort(key=lambda x: x[0], reverse=True)
    n_active    = len(scored)
    base_alloc  = min(total_budget / n_active, per_sym_cap)

    for quality, result in scored:
        sym    = result.get("market", {}).get("symbol", "")
        regime = result.get("regime", {})
        vga    = result.get("vga", "mixed")
        mult   = float(regime.get("size_multiplier", 1.0))
        name   = regime.get("regime", "mixed")

        risk   = round(base_alloc * mult, 2)

        if risk < min_risk_dollars:
            inactive.append(SymbolAllocation(
                symbol=sym, regime=name, vga_environment=vga,
                allowed=False, risk_dollars=0, size_multiplier=mult,
                rationale=f"Allocation ${risk:.0f} below minimum ${min_risk_dollars:.0f}.",
            ))
            continue

        active.append(SymbolAllocation(
            symbol=sym, regime=name, vga_environment=vga,
            allowed=True, risk_dollars=risk, size_multiplier=mult,
            rationale=(
                f"{vga.replace('_',' ').title()} regime "
                f"(quality={quality:.0%}, multiplier={mult:.0%}) → "
                f"${risk:.0f} risk budget."
            ),
        ))

    # Summary notes
    total_deployed = sum(a.risk_dollars for a in active)
    notes.append(
        f"Allocating ${total_deployed:,.0f} total risk across "
        f"{len(active)} symbol(s)."
    )
    if len(inactive) > 0:
        syms = [i.symbol for i in inactive]
        notes.append(f"Skipped: {', '.join(syms)}.")
    if n_active > 1:
        notes.append("Equal-weight base allocation. Scaled by regime size multiplier.")

    mode = "equal_weight_regime_scaled" if n_active > 1 else "single_symbol"

    return PortfolioAllocation(
        total_risk_budget=total_deployed,
        per_symbol=active + inactive,
        active_symbols=[a.symbol for a in active],
        inactive_symbols=[i.symbol for i in inactive],
        allocation_mode=mode,
        notes=notes,
    )


def apply_allocation_to_result(
    result:     dict[str, Any],
    allocation: PortfolioAllocation,
) -> dict[str, Any]:
    """
    Inject the allocated risk budget back into an engine result.
    Updates contracts on each candidate based on allocated risk dollars.
    """
    sym = result.get("market", {}).get("symbol", "")
    sym_alloc = next(
        (a for a in allocation.per_symbol if a.symbol == sym and a.allowed),
        None,
    )
    if not sym_alloc:
        return result

    from calculator.risk_engine import compute_contracts
    budget = sym_alloc.risk_dollars

    for c in result.get("candidates", []):
        max_loss = c.get("max_loss", 0)
        if max_loss and max_loss > 0:
            c["contracts"] = compute_contracts(budget, max_loss)

    result["allocated_risk_dollars"] = budget
    result["allocation_rationale"]   = sym_alloc.rationale
    return result
