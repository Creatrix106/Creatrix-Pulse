"""Server-side text formatting for insights.

Insight titles embed formatted numbers ("₹12,34,567", "+12.3%"), and the frontend only *renders* insights, so
the server must format exactly like the browser's ``Intl`` formatters (src/utils/format.ts):

* CLDR data (grouping, symbols, separators, month names) comes from Babel;
* rounding is "half away from zero" like ICU / ``Number.prototype.toFixed`` – Python's ``round``/``format``
  round half to even and would differ on exact ties (e.g. 0.25 → "0.3" in JS, "0.2" in Python).
"""

import math
import re
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from babel import Locale, UnknownLocaleError
from babel.dates import format_skeleton
from babel.numbers import format_currency, format_decimal, list_currencies

_FRACTION = re.compile(r"\.[0#]+")


def to_fixed(value: float, digits: int) -> str:
    """``Number.prototype.toFixed``: exact binary value, ties away from zero."""
    if value == 0:
        value = 0.0  # JS prints -0 as "0"
    return format(Decimal(value).quantize(Decimal(1).scaleb(-digits), rounding=ROUND_HALF_UP), "f")


def js_round(value: float) -> int:
    """``Math.round``: ties toward +infinity."""
    return math.floor(value + 0.5)


def _quantize(value: float, digits: int) -> Decimal:
    return Decimal(value).quantize(Decimal(1).scaleb(-digits), rounding=ROUND_HALF_UP)


@dataclass(frozen=True, slots=True)
class Formatters:
    currency_code: str
    locale: Locale
    _currency_pattern: str
    _number_pattern: str

    @classmethod
    def create(cls, currency: str, locale: str) -> Formatters:
        code = currency.upper()
        if code not in list_currencies():
            raise ValueError(f"Unknown currency “{currency}”.")
        try:
            parsed = Locale.parse(locale.replace("-", "_"))
        except UnknownLocaleError, ValueError:
            raise ValueError(f"Unknown locale “{locale}”.") from None
        return cls(
            currency_code=code,
            locale=parsed,
            # Intl: maximumFractionDigits 0 for currency, 1 for plain numbers – keep each locale's own grouping.
            _currency_pattern=_FRACTION.sub("", parsed.currency_formats["standard"].pattern),
            _number_pattern=_FRACTION.sub(".#", parsed.decimal_formats[None].pattern),
        )

    def currency(self, value: float) -> str:
        return format_currency(
            _quantize(value, 0),
            self.currency_code,
            format=self._currency_pattern,
            locale=self.locale,
            currency_digits=False,
        )

    def number(self, value: float) -> str:
        return format_decimal(_quantize(value, 1), format=self._number_pattern, locale=self.locale)

    @staticmethod
    def percent(value: float, *, signed: bool = False, digits: int = 1) -> str:
        """Takes a value that is already a percentage (12.3 → "12.3%"). Not locale dependent, like the frontend."""
        sign = "+" if signed and value > 0 else ""
        return f"{sign}{to_fixed(value, digits)}%"

    def date(self, day: date, style: Literal["short", "long"] = "short") -> str:
        return format_skeleton("yMMMd" if style == "long" else "MMMd", day, locale=self.locale)
