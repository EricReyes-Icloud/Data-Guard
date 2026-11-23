from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

THOUSANDS_SEPARATORS = {
    "es_AR": ".",
    "en_US": ",",
}
DECIMAL_SEPARATORS = {
    "es_AR": ",",
    "en_US": ".",
}


def parse_price(value: str, *, locale: str = "es_AR") -> Decimal:
    """Parsea un precio según el locale del proveedor y lo cuantiza a 0.01."""
    raw = value.strip()
    if raw == "":
        raise ValueError("El precio está vacío")

    thousands = THOUSANDS_SEPARATORS.get(locale)
    decimal_sep = DECIMAL_SEPARATORS.get(locale)
    if thousands is None or decimal_sep is None:
        raise ValueError(f"Locale no soportado: {locale}")

    normalized = raw.replace(thousands, "").replace(decimal_sep, ".")
    try:
        amount = Decimal(normalized)
    except InvalidOperation as exc:
        raise ValueError(f"Precio no parseable: {value!r}") from exc

    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
