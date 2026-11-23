from dataguard.domain import Rule, Severidad


def _non_empty(field: str):
    return lambda row: str(row.get(field, "")).strip() != ""


RULES: dict[str, Rule] = {
    "PRODUCT_NON_EMPTY": Rule(
        id="PRODUCT_NON_EMPTY",
        field="producto",
        severity=Severidad.CRITICAL,
        check=_non_empty("producto"),
        message="El producto está vacío",
    ),
    "PRICE_FORMAT": Rule(
        id="PRICE_FORMAT",
        field="precio",
        severity=Severidad.CRITICAL,
        check=lambda row: row.get("precio_parse_error") is None,
        message="El precio no tiene un formato numérico válido",
    ),
    "PRICE_POSITIVE": Rule(
        id="PRICE_POSITIVE",
        field="precio",
        severity=Severidad.CRITICAL,
        check=lambda row: row.get("precio") is None or row.get("precio") > 0,
        message="El precio debe ser mayor que cero",
    ),
    "CATEGORY_NON_EMPTY": Rule(
        id="CATEGORY_NON_EMPTY",
        field="categoria",
        severity=Severidad.CRITICAL,
        check=_non_empty("categoria"),
        message="La categoría está vacía",
    ),
    "CATEGORY_IN_CATALOG": Rule(
        id="CATEGORY_IN_CATALOG",
        field="categoria",
        severity=Severidad.CRITICAL,
        check=lambda row: row.get("category_match_kind") in {"exact", "alias"},
        message="La categoría no existe en el catálogo de la PYME",
    ),
    "DUPLICATE_ROW": Rule(
        id="DUPLICATE_ROW",
        field="fila",
        severity=Severidad.WARNING,
        check=lambda row: not row.get("is_duplicate", False),
        message="Fila exactamente duplicada",
    ),
    "PRICE_CONFLICT": Rule(
        id="PRICE_CONFLICT",
        field="fila",
        severity=Severidad.CRITICAL,
        check=lambda row: not row.get("has_price_conflict", False),
        message="El mismo producto normalizado tiene precios distintos",
    ),
}


def build_rules(active_ids: list[str] | None = None) -> list[Rule]:
    if active_ids is None:
        return list(RULES.values())
    missing = [rule_id for rule_id in active_ids if rule_id not in RULES]
    if missing:
        raise ValueError(f"Reglas desconocidas: {', '.join(missing)}")
    return [RULES[rule_id] for rule_id in active_ids]
