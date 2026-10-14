#!/usr/bin/env python3
"""Create a NIFTY CE/PE settlement-price window from an NSE option CSV.

The script finds the latest Date in the CSV automatically.  For the entered
base strike it uses the four listed strikes above and below it, then prints
CE, PE, CE + PE, and their average for every strike in that nine-strike window.
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path


DEFAULT_CSV = Path(
    r"C:\Users\Ramnarendran\Downloads\Quote-Derivative-NIFTY-14-09-2026-14-10-2026.csv"
)

DATE_FORMAT = "%d-%b-%Y"


def to_number(value: str) -> float | None:
    """Convert NSE-formatted values such as '23,400.00' to a number."""
    try:
        return float((value or "").replace(",", "").strip())
    except ValueError:
        return None


def to_date(value: str):
    """Parse dates used by NSE exports."""
    value = (value or "").strip()
    for fmt in ("%d-%b-%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    return None


def display(value: float | None) -> str:
    if value is None:
        return "—"
    return str(int(value)) if value.is_integer() else f"{value:.2f}".rstrip("0").rstrip(".")


def read_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open("r", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        required = {"Date", "Option Type", "Strike Price", "Settlement Price"}
        found = set(reader.fieldnames or [])
        missing = required - found
        if missing:
            raise ValueError("Missing required CSV columns: " + ", ".join(sorted(missing)))
        return list(reader)


def calculate_window(rows: list[dict[str, str]], base_strike: float):
    dates = [to_date(row["Date"]) for row in rows]
    valid_dates = [item for item in dates if item is not None]
    if not valid_dates:
        raise ValueError("The Date column has no valid dates.")

    latest_date = max(valid_dates)
    latest_rows = [row for row in rows if to_date(row["Date"]) == latest_date]

    prices: dict[tuple[float, str], float] = {}
    strikes: set[float] = set()
    for row in latest_rows:
        strike = to_number(row["Strike Price"])
        settlement = to_number(row["Settlement Price"])
        option_type = row["Option Type"].strip().upper()
        if strike is None:
            continue
        strikes.add(strike)
        if option_type in {"CE", "PE"} and settlement is not None:
            prices[(strike, option_type)] = settlement

    ordered_strikes = sorted(strikes)
    if base_strike not in strikes:
        nearest = sorted(ordered_strikes, key=lambda strike: abs(strike - base_strike))[:5]
        nearby = ", ".join(display(strike) for strike in sorted(nearest))
        raise ValueError(
            f"Strike {display(base_strike)} is unavailable on {latest_date:%d-%b-%Y}. "
            f"Nearby available strikes: {nearby}"
        )

    base_index = ordered_strikes.index(base_strike)
    window = ordered_strikes[max(0, base_index - 4) : base_index + 5]
    if len(window) != 9:
        raise ValueError("There are not four available strikes on both sides of the chosen strike.")

    result = []
    for strike in reversed(window):  # highest strike first, matching the reference image
        ce = prices.get((strike, "CE"))
        pe = prices.get((strike, "PE"))
        total = ce + pe if ce is not None and pe is not None else None
        average = total / 2 if total is not None else None
        result.append((strike, ce, pe, total, average))
    return latest_date, result


def print_table(latest_date, base_strike: float, result) -> None:
    print(f"Latest data date used: {latest_date:%d-%b-%Y}")
    print(f"ATM strike base: {display(base_strike)}\n")
    print("Final processed NIFTY option window")
    print(f"{'Strike':>8}  {'CE':>10}  {'PE':>10}  {'Total (CE + PE)':>16}  {'Average':>10}")
    print("-" * 62)
    for strike, ce, pe, total, average in result:
        print(
            f"{display(strike):>8}  {display(ce):>10}  {display(pe):>10}  "
            f"{display(total):>16}  {display(average):>10}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("strike", nargs="?", type=float, help="Base/ATM strike, for example 22700")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV, help="Path to the NSE CSV file")
    args = parser.parse_args()

    try:
        base_strike = args.strike
        if base_strike is None:
            base_strike = to_number(input("Enter base strike: "))
        if base_strike is None:
            raise ValueError("Enter a valid numeric strike.")
        latest_date, result = calculate_window(read_rows(args.csv), base_strike)
        print_table(latest_date, base_strike, result)
        return 0
    except (OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
