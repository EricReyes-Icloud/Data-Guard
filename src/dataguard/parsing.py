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

    integer_part = raw.lstrip("+-").split(decimal_sep, 1)[0]
    if thousands in integer_part:
        head, *groups = integer_part.split(thousands)
        grouped = head.isdigit() and 1 <= len(head) <= 3 and all(
            len(group) == 3 and group.isdigit() for group in groups
        )
        if not grouped:
            raise ValueError(f"Agrupación de miles inválida: {value!r}")

    normalized = raw.replace(thousands, "").replace(decimal_sep, ".")
    try:
        amount = Decimal(normalized)
    except InvalidOperation as exc:
        raise ValueError(f"Precio no parseable: {value!r}") from exc

    if not amount.is_finite():
        raise ValueError(f"Precio no finito: {value!r}")
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
