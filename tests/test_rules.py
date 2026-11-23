from decimal import Decimal

from dataguard.domain import Severidad
from dataguard.rules import build_rules


def test_product_non_empty_rejects_blank():
    rules = {r.id: r for r in build_rules(["PRODUCT_NON_EMPTY"])}
    assert rules["PRODUCT_NON_EMPTY"].check({"producto": ""}) is False
    assert rules["PRODUCT_NON_EMPTY"].check({"producto": "Cafe"}) is True


def test_price_positive_rejects_zero_and_negative():
    rules = {r.id: r for r in build_rules(["PRICE_POSITIVE"])}
    assert rules["PRICE_POSITIVE"].check({"precio": Decimal("0.00")}) is False
    assert rules["PRICE_POSITIVE"].check({"precio": Decimal("-1.00")}) is False
    assert rules["PRICE_POSITIVE"].check({"precio": Decimal("10.00")}) is True
