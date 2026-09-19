"""
converter.py

Basis calculation, price conversion, AND the command-line entry point
that ties config -> market_data -> parser -> converter -> formatter
together.

Conversion is one-directional and explicit:

    basis = nq_price - us100_price
    us100_level = nq_level - basis

This module (and this application) is a converter / information tool
ONLY. It NEVER places trades, sends orders, or talks to any
brokerage/execution API. It only transforms numeric text that the
user pastes in, for reference purposes.

Run directly as:

    python converter.py                 # live mode
    python converter.py --manual        # manual price entry
    python converter.py --save          # also save output to a file
    python converter.py --no-copy       # skip clipboard prompt
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from formatter import format_basis_display, format_price_clean, format_price_display
from parser import GammaLine, parse_block

SEPARATOR = "=" * 50


@dataclass(frozen=True)
class ConversionResult:
    nq_price: float
    us100_price: float
    basis: float
    converted_lines: List[str]
    warnings: List[str]


def calculate_basis(nq_price: float, us100_price: float) -> float:
    """basis = NQ price - US100 price."""
    return nq_price - us100_price


def convert_level(nq_level: float, basis: float) -> float:
    """US100 level = NQ level - basis."""
    return nq_level - basis


def convert_gamma_line(gamma_line: GammaLine, basis: float) -> str:
    """
    Convert one already-parsed GammaLine into its output text.

    Only the fields listed in gamma_line.price_indices are converted;
    everything else (label, other fields, descriptive text) is passed
    through unchanged.
    """
    if gamma_line.is_blank:
        return gamma_line.raw

    if not gamma_line.is_valid:
        # Never corrupt input we couldn't confidently parse: pass it
        # through exactly as received.
        return gamma_line.raw

    new_fields = list(gamma_line.fields)
    for idx in gamma_line.price_indices:
        original_price = float(new_fields[idx])
        converted_price = convert_level(original_price, basis)
        new_fields[idx] = format_price_clean(converted_price)

    return ", ".join([gamma_line.label, *new_fields])


def convert_block(
    gamma_lines: List[GammaLine],
    nq_price: float,
    us100_price: float,
) -> ConversionResult:
    """
    Convert a full list of parsed GammaLines. Lines that failed to
    parse are preserved unchanged and reported in `warnings` rather
    than silently dropped or guessed at.
    """
    basis = calculate_basis(nq_price, us100_price)
    converted_lines: List[str] = []
    warnings: List[str] = []

    for gamma_line in gamma_lines:
        if not gamma_line.is_blank and not gamma_line.is_valid:
            warnings.append(
                f"Could not parse line: '{gamma_line.raw}' ({gamma_line.error})"
            )
        converted_lines.append(convert_gamma_line(gamma_line, basis))

    return ConversionResult(
        nq_price=nq_price,
        us100_price=us100_price,
        basis=basis,
        converted_lines=converted_lines,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# CLI orchestration
# ---------------------------------------------------------------------------
# Everything below wires the pure logic above together with config.py and
# market_data.py, and handles user interaction (stdin, stdout, clipboard,
# filesystem). No pricing/parsing logic is duplicated here.


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="converter.py",
        description=(
            "NQ -> US100 Gamma Converter. Converts Gamma Engine [IB15] "
            "price levels from NQ futures terms to US100 CFD terms using "
            "the current basis. This tool is informational only and "
            "never places trades."
        ),
    )
    parser.add_argument(
        "--manual",
        action="store_true",
        help="Manually enter NQ and US100 prices instead of fetching live data.",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save the converted output to output/converted_<timestamp>.txt",
    )
    parser.add_argument(
        "--no-copy",
        action="store_true",
        help="Disable clipboard copy of the converted output.",
    )
    return parser


def get_live_prices(provider) -> Optional[tuple]:
    """Fetch (nq_price, us100_price) from a provider, or None on failure."""
    from market_data import MarketDataError

    try:
        nq_price = provider.get_nq_price()
        us100_price = provider.get_us100_price()
    except MarketDataError as exc:
        print(f"ERROR: {exc}")
        return None
    return nq_price, us100_price


def prompt_manual_prices() -> Optional[tuple]:
    """Interactively prompt for manual NQ/US100 prices. Returns None on bad input."""
    try:
        nq_raw = input("NQ1! price: ").strip()
        us100_raw = input("US100 price: ").strip()
    except EOFError:
        print("ERROR: No input received.")
        return None

    try:
        nq_price = float(nq_raw)
    except ValueError:
        print(f"ERROR: Invalid NQ1! price: '{nq_raw}'")
        return None

    try:
        us100_price = float(us100_raw)
    except ValueError:
        print(f"ERROR: Invalid US100 price: '{us100_raw}'")
        return None

    if nq_price <= 0:
        print(f"ERROR: NQ1! price must be positive, got {nq_price}.")
        return None
    if us100_price <= 0:
        print(f"ERROR: US100 price must be positive, got {us100_price}.")
        return None

    return nq_price, us100_price


def read_multiline_block() -> str:
    """Read lines from stdin until an empty line (or EOF) is entered."""
    print("Paste Gamma Engine [IB15] input.")
    print("Press ENTER on an empty line when finished.")
    print()
    lines: List[str] = []
    while True:
        try:
            line = input("> ")
        except EOFError:
            break
        if line.strip() == "":
            break
        lines.append(line)
    return "\n".join(lines)


def print_summary(nq_price: float, us100_price: float, basis: float) -> None:
    print()
    print(SEPARATOR)
    print("CONVERSION RESULT")
    print(SEPARATOR)
    print(f"NQ1!:       {format_price_display(nq_price)}")
    print(f"US100:      {format_price_display(us100_price)}")
    print(f"Basis:      {format_basis_display(basis)}")
    print()
    print("Formula:")
    print()
    print(f"US100 = NQ - {format_basis_display(basis)}")
    print(SEPARATOR)
    print()

    if basis <= 0:
        print(
            "WARNING: Basis is zero or negative. NQ futures normally trade "
            "at a premium to the US100 cash/CFD index, so this may indicate "
            "stale, incorrect, or unusual market data. Double-check your "
            "prices before relying on this conversion."
        )
        print()


def offer_clipboard_copy(text: str, no_copy: bool) -> None:
    if no_copy:
        return

    try:
        answer = input("Copy converted output to clipboard? [Y/n] ").strip().lower()
    except EOFError:
        answer = "n"

    if answer not in ("", "y", "yes"):
        return

    try:
        import pyperclip

        pyperclip.copy(text)
        print("Copied to clipboard.")
    except ImportError:
        print(
            "NOTE: pyperclip is not installed, so the result was not copied "
            "to the clipboard. The output above is still complete."
        )
    except Exception as exc:  # pyperclip can raise platform-specific errors
        print(f"NOTE: Clipboard copy failed ({exc}). The output above is still complete.")


def save_output(result: ConversionResult, converted_text: str) -> Optional[str]:
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(output_dir, f"converted_{timestamp}.txt")

    lines = [
        SEPARATOR,
        "NQ -> US100 GAMMA CONVERTER - SAVED OUTPUT",
        SEPARATOR,
        f"Timestamp:  {datetime.now().isoformat(timespec='seconds')}",
        f"NQ1!:       {format_price_display(result.nq_price)}",
        f"US100:      {format_price_display(result.us100_price)}",
        f"Basis:      {format_basis_display(result.basis)}",
        SEPARATOR,
        "",
        converted_text,
        "",
    ]

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
    except OSError as exc:
        print(f"ERROR: Could not save output ({exc}).")
        return None

    return file_path


def run(argv: Optional[List[str]] = None) -> int:
    from config import load_config
    from market_data import MarketDataError, build_live_provider

    args = build_arg_parser().parse_args(argv)

    print(SEPARATOR)
    print("NQ -> US100 GAMMA CONVERTER")
    print(SEPARATOR)
    print()
    print(
        "This tool converts Gamma Engine [IB15] price levels for reference "
        "only. It does not place trades or send orders."
    )
    print()

    if args.manual:
        prices = prompt_manual_prices()
    else:
        config = load_config()
        try:
            provider = build_live_provider(config)
        except MarketDataError as exc:
            print(f"ERROR: {exc}")
            print(
                "Configure MARKET_DATA_API_URL, NQ_SYMBOL, US100_SYMBOL "
                "(and MARKET_DATA_API_KEY if required) in your .env file, "
                "or run with --manual to enter prices by hand."
            )
            return 1

        print("Fetching market data...")
        prices = get_live_prices(provider)

    if prices is None:
        return 1

    nq_price, us100_price = prices

    print()
    print(f"NQ1!: {format_price_display(nq_price)}")
    print(f"US100: {format_price_display(us100_price)}")

    basis = calculate_basis(nq_price, us100_price)
    print(f"Basis: {format_basis_display(basis)}")
    print()

    raw_block = read_multiline_block()
    if not raw_block.strip():
        print("ERROR: No Gamma Engine input was provided.")
        return 1

    gamma_lines = parse_block(raw_block)
    result = convert_block(gamma_lines, nq_price, us100_price)

    for warning in result.warnings:
        print()
        print("WARNING:")
        print(warning)

    converted_text = "\n".join(result.converted_lines)

    print_summary(result.nq_price, result.us100_price, result.basis)
    print(converted_text)
    print()
    print(SEPARATOR)

    offer_clipboard_copy(converted_text, args.no_copy)

    if args.save:
        saved_path = save_output(result, converted_text)
        if saved_path:
            print(f"Saved to {saved_path}")

    return 0


if __name__ == "__main__":
    sys.exit(run())
