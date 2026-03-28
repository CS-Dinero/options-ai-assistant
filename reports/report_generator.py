"""reports/report_generator.py — Morning brief, trade log, weekly review."""
from __future__ import annotations
from datetime import date
import csv, io, os
from dataclasses import dataclass

@dataclass
class TradeLogEntry:
    trade_id: str; date_opened: str; symbol: str; structure: str
    option_type: str; long_strike: float; long_expiry: str
    short_strike: float; short_expiry: str; entry_debit: float
    contracts: int; candidate_score: float; roll_score: float
    status: str = "OPEN"; harvest_credit: float = 0.0
    roll_credit: float = 0.0; roll_cost: float = 0.0
    realized_pnl: float = 0.0; notes: str = ""; date_closed: str = ""

def generate_morning_brief(candidates: list[dict], symbol: str, spot: float,
                            capital: float = 25_000.0, contracts: int = 1) -> str:
    today = date.today().isoformat()
    if not candidates or "error" in (candidates[0] if candidates else {}):
        return f"No candidates found for {symbol} today ({today})"
    top = candidates[0]
    debit_total = top.get("entry_net_debit", 0) * contracts * 100
    lines = [
        f"{'='*55}",
        f"  OPTIONS AI ASSISTANT — MORNING BRIEF",
        f"  {today}  |  {symbol}  |  Spot: ${spot:.2f}",
        f"  Capital: ${capital:,.0f}  |  Contracts: {contracts}",
        f"{'='*55}",
        "",
        f"  🏆 BEST CANDIDATE — PLACE THIS TRADE",
        f"  {'─'*51}",
        f"  Structure:   Deep ITM {top.get('option_type','PUT')} Calendar",
        f"  Entry Debit: ${top.get('entry_net_debit',0):.2f}/contract = ${debit_total:.2f} total",
        "",
        f"  ── BUY (Long Leg) ──────────────────────────",
        f"  Strike:  {top.get('long_strike','')} {top.get('option_type','PUT')}",
        f"  Expiry:  {top.get('long_expiry','')}  (DTE {top.get('long_dte','')})",
        f"  Mid:     ${top.get('long_mid',0):.2f}   Delta: {top.get('long_delta','N/A')}",
        "",
        f"  ── SELL (Short Leg) ────────────────────────",
        f"  Strike:  {top.get('short_strike','')} {top.get('option_type','PUT')}",
        f"  Expiry:  {top.get('short_expiry','')}  (DTE {top.get('short_dte','')})",
        f"  Mid:     ${top.get('short_mid',0):.2f}   Delta: {top.get('short_delta','N/A')}",
        "",
        f"  ── Quality ─────────────────────────────────",
        f"  Cheapness:       {top.get('entry_cheapness_score',0):.1f}/100",
        f"  Roll Score:      {top.get('future_roll_score',0):.1f}/100",
        f"  Recovery Ratio:  {top.get('projected_recovery_ratio',0):.2f}x",
        f"  Candidate Score: {top.get('candidate_score',0):.1f}/100",
        "",
        f"  ── How to Place ────────────────────────────",
        f"  TRADIER: Options → Spread → Calendar",
        f"  SCHWAB:  Trade → Options → Spreads → Calendar",
        f"  Same symbol, same type, same strike if diagonal",
        f"  ⚠ Confirm live bid/ask before submitting",
        f"{'─'*55}",
    ]
    if len(candidates) > 1:
        lines.append("  OTHER CANDIDATES:")
        for i, c in enumerate(candidates[1:5], 2):
            lines.append(
                f"  #{i}  {c.get('short_strike','')}/{c.get('long_strike','')} | "
                f"Debit ${c.get('entry_net_debit',0):.2f} | Score {c.get('candidate_score',0):.0f}")
        lines.append("")
    lines += [
        f"  📊 BASIS RECOVERY TARGETS",
        f"  {'─'*51}",
        f"  Entry debit:      ${top.get('entry_net_debit',0):.2f}",
        f"  Harvest zone:     ${top.get('entry_net_debit',0)*0.30:.2f}–${top.get('entry_net_debit',0)*0.50:.2f} credit captured",
        f"  Full recovery:    ${top.get('entry_net_debit',0):.2f} in credits collected",
        f"{'='*55}",
    ]
    return "\n".join(lines)

def generate_scanner_csv(candidates: list[dict]) -> str:
    if not candidates or "error" in (candidates[0] if candidates else {}):
        return "No candidates\n"
    fields = ["symbol","option_type","short_strike","short_expiry","short_dte",
              "long_strike","long_expiry","long_dte","entry_net_debit",
              "long_intrinsic_value","long_extrinsic_cost","entry_debit_width_ratio",
              "projected_recovery_ratio","future_roll_score","entry_cheapness_score",
              "candidate_score","liquidity_score","expected_move_clearance"]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    w.writeheader(); w.writerows(candidates)
    return buf.getvalue()

def log_trade(log_path: str, entry: TradeLogEntry) -> None:
    fields = list(entry.__dataclass_fields__.keys())
    exists = os.path.exists(log_path)
    with open(log_path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        if not exists: w.writeheader()
        w.writerow({k: getattr(entry, k) for k in fields})

def load_trade_log(log_path: str) -> list[TradeLogEntry]:
    if not os.path.exists(log_path): return []
    entries = []
    with open(log_path, newline="") as f:
        for row in csv.DictReader(f):
            try:
                entries.append(TradeLogEntry(
                    trade_id=row["trade_id"], date_opened=row["date_opened"],
                    symbol=row["symbol"], structure=row["structure"],
                    option_type=row["option_type"], long_strike=float(row["long_strike"]),
                    long_expiry=row["long_expiry"], short_strike=float(row["short_strike"]),
                    short_expiry=row["short_expiry"], entry_debit=float(row["entry_debit"]),
                    contracts=int(row["contracts"]), candidate_score=float(row["candidate_score"]),
                    roll_score=float(row["roll_score"]), status=row.get("status","OPEN"),
                    harvest_credit=float(row.get("harvest_credit",0)),
                    roll_credit=float(row.get("roll_credit",0)),
                    roll_cost=float(row.get("roll_cost",0)),
                    realized_pnl=float(row.get("realized_pnl",0)),
                    notes=row.get("notes",""), date_closed=row.get("date_closed","")))
            except Exception: continue
    return entries

def generate_weekly_review(trades: list[TradeLogEntry], capital: float = 25_000.0) -> str:
    today = date.today().isoformat()
    open_t   = [t for t in trades if t.status == "OPEN"]
    closed_t = [t for t in trades if t.status == "CLOSED"]
    total_invested = sum(t.entry_debit * t.contracts * 100 for t in trades)
    total_harvested= sum((t.harvest_credit + t.roll_credit) * t.contracts * 100 for t in trades)
    total_costs    = sum(t.roll_cost * t.contracts * 100 for t in trades)
    net_gain = total_harvested - total_costs
    pct = net_gain / capital * 100 if capital > 0 else 0
    lines = [
        f"{'='*55}",
        f"  WEEKLY REVIEW — {today}",
        f"{'='*55}",
        f"  Capital:            ${capital:,.0f}",
        f"  Open campaigns:     {len(open_t)}",
        f"  Closed campaigns:   {len(closed_t)}",
        f"  Total invested:     ${total_invested:,.2f}",
        f"  Total harvested:    ${total_harvested:,.2f}",
        f"  Total roll costs:   ${total_costs:,.2f}",
        f"  Net gain:           ${net_gain:+,.2f}",
        f"  Return on capital:  {pct:+.3f}%",
        f"",
        f"  CAMPAIGNS:",
    ]
    for t in trades:
        net = (t.harvest_credit + t.roll_credit - t.roll_cost) * t.contracts * 100
        lines.append(
            f"  {t.symbol} {t.short_strike}/{t.long_strike} {t.structure} "
            f"| {t.status} | Debit ${t.entry_debit:.2f}x{t.contracts} "
            f"| Net ${net:+.2f}")
    lines.append(f"{'='*55}")
    return "\n".join(lines)
