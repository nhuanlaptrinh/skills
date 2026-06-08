#!/usr/bin/env python3
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP
import re
import sys

VAT_RATE_PERCENT = Decimal("8")
ROUND_TO = Decimal("1000")


def parse_amount(value: str) -> Decimal:
    text = value.strip().lower()
    multiplier = Decimal("1000") if "k" in text else Decimal("1")
    digits = re.sub(r"[^0-9]", "", text)
    if not digits:
        raise ValueError(f"Cannot parse amount: {value}")
    return Decimal(digits) * multiplier


def format_vnd(amount: Decimal) -> str:
    return f"{int(amount):,}".replace(",", ".")


def calculate(subtotal: Decimal) -> tuple[Decimal, Decimal, Decimal]:
    vat = (subtotal * VAT_RATE_PERCENT / Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    raw_total = subtotal + vat
    rounded_total = (raw_total / ROUND_TO).to_integral_value(rounding=ROUND_CEILING) * ROUND_TO
    return vat, raw_total, rounded_total


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: calc_rounded_tuition.py <amount> [amount...]", file=sys.stderr)
        return 2

    for arg in sys.argv[1:]:
        subtotal = parse_amount(arg)
        vat, raw_total, rounded_total = calculate(subtotal)
        print(
            f"{arg}: subtotal={format_vnd(subtotal)} VAT8={format_vnd(vat)} "
            f"raw_total={format_vnd(raw_total)} rounded_total={format_vnd(rounded_total)}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
