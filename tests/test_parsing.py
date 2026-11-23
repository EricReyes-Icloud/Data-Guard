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
