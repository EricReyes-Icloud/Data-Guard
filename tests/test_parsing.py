from decimal import Decimal

import pytest

from dataguard.parsing import parse_price


def test_parses_es_ar_thousands_and_decimal():
    assert parse_price("1.234,56", locale="es_AR") == Decimal("1234.56")


def test_parses_simple_integer():
    assert parse_price("100", locale="es_AR") == Decimal("100.00")


def test_rejects_unparseable_value():
    with pytest.raises(ValueError):
        parse_price("ABC", locale="es_AR")


def test_rejects_empty_value():
    with pytest.raises(ValueError):
        parse_price("", locale="es_AR")


def test_rejects_non_finite_value():
    for value in ("NaN", "Infinity", "-Infinity"):
        with pytest.raises(ValueError):
            parse_price(value, locale="es_AR")


def test_rejects_malformed_thousands_grouping():
    with pytest.raises(ValueError):
        parse_price("1.2.3,45", locale="es_AR")
    with pytest.raises(ValueError):
        parse_price("1,23,456", locale="en_US")


def test_parses_en_us_grouping_and_keeps_ungrouped_values():
    assert parse_price("1,234.56", locale="en_US") == Decimal("1234.56")
    assert parse_price("1234,56", locale="es_AR") == Decimal("1234.56")
