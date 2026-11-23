import json
from pathlib import Path

import yaml

from dataguard.catalog import load_catalog
from dataguard.domain import Estado, Hallazgo, Severidad, Veredicto
from dataguard.matching import match_category
from dataguard.normalization import hygiene_trace, normalize
from dataguard.parsing import parse_price
from dataguard.reading import read_supplier
from dataguard.report import write_outputs
from dataguard.rules import build_rules


def _load_config(config_path: str | Path) -> dict:
    with Path(config_path).open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _is_duplicate(candidate: dict, seen: list[dict]) -> bool:
    key = (candidate["producto_norm"], candidate["categoria_norm"], candidate["precio_raw_norm"])
    for prev in seen:
        prev_key = (prev["producto_norm"], prev["categoria_norm"], prev["precio_raw_norm"])
        if prev_key == key:
            return True
    return False


def _price_conflicts(rows: list[dict]) -> set[int]:
    by_product: dict[str, set[str]] = {}
    for row in rows:
        if row["is_duplicate"]:
            continue
        if row["producto_norm"] == "" or row["precio"] is None:
            continue
        by_product.setdefault(row["producto_norm"], set()).add(str(row["precio"]))
    conflicts: set[int] = set()
    for row in rows:
        if row["is_duplicate"]:
            continue
        prices = by_product.get(row["producto_norm"], set())
        if len(prices) > 1:
            conflicts.add(row["numero"])
    return conflicts


def validate(
    supplier_path: str | Path,
    config_path: str | Path,
    *,
    output_dir: str | Path | None = None,
) -> dict:
    config = _load_config(config_path)
    supplier_path = Path(supplier_path)
    output_dir = Path(output_dir) if output_dir else supplier_path.parent

    lectura = read_supplier(
        supplier_path,
        header_row=int(config.get("header_row", 1)),
        sheet=config.get("sheet", 0),
        column_map=config.get("column_map"),
    )
    catalog = load_catalog(
        config["catalogo"],
        sheet=config.get("catalog_sheet", 0),
        column_map=config.get("catalog_column_map"),
    )
    rules = build_rules(config.get("reglas_activas"))

    processed: list[dict] = []
    seen: list[dict] = []
    for numero, raw in lectura.filas:
        producto_raw = raw.get("producto") or ""
        categoria_raw = raw.get("categoria") or ""
        precio_raw = raw.get("precio") or ""

        producto_norm = normalize(producto_raw, "match")
        categoria_norm = normalize(categoria_raw, "match")
        precio_raw_norm = normalize(precio_raw, "match")

        precio = None
        precio_error = None
        if precio_raw_norm != "":
            try:
                precio = parse_price(precio_raw, locale=config.get("locale", "es_AR"))
            except ValueError as exc:
                precio_error = str(exc)

        match = match_category(categoria_raw, catalog) if categoria_norm != "" else None
        categoria_canonica = normalize(categoria_raw, "display")
        if match and match.canonical:
            categoria_canonica = catalog.display_names.get(match.canonical, categoria_canonica)

        row = {
            "numero": numero,
            "producto_raw": producto_raw,
            "categoria_raw": categoria_raw,
            "precio_raw": precio_raw,
            "producto": normalize(producto_raw, "display"),
            "categoria": normalize(categoria_raw, "display"),
            "categoria_canonica": categoria_canonica,
            "producto_norm": producto_norm,
            "categoria_norm": categoria_norm,
            "precio_raw_norm": precio_raw_norm,
            "precio": precio,
            "precio_parse_error": precio_error,
            "higiene": hygiene_trace(producto_raw) + hygiene_trace(categoria_raw),
            "category_match": match,
            "category_match_kind": match.kind if match else "no_match",
            "is_duplicate": False,
            "has_price_conflict": False,
        }
        row["is_duplicate"] = _is_duplicate(row, seen)
        seen.append(row)
        processed.append(row)

    conflict_rows = _price_conflicts(processed)
    for row in processed:
        row["has_price_conflict"] = row["numero"] in conflict_rows

    verdicts: list[Veredicto] = []
    records: list[dict] = []
    discarded = 0

    for row in processed:
        hallazgos: list[Hallazgo] = []

        # Duplicado exacto: se descarta con conteo.
        if row["is_duplicate"]:
            hallazgos.append(Hallazgo(
                fila=row["numero"], campo="fila", regla_id="DUPLICATE_ROW",
                severidad=Severidad.WARNING, valor_original=row["producto_raw"],
                valor_sugerido=None, score=None,
            ))
            veredicto = Veredicto(fila=row["numero"], estado=Estado.RECHAZADO, hallazgos=tuple(hallazgos))
            verdicts.append(veredicto)
            records.append({"row": row, "verdict": veredicto, "discarded": True})
            discarded += 1
            continue

        for rule in rules:
            if rule.id == "DUPLICATE_ROW":
                continue
            if rule.id == "CATEGORY_IN_CATALOG":
                match = row["category_match"]
                kind = match.kind if match else "no_match"
                if kind in {"exact", "alias"}:
                    continue
                if kind == "fuzzy":
                    hallazgos.append(Hallazgo(
                        fila=row["numero"], campo="categoria", regla_id=rule.id,
                        severidad=Severidad.CORRECTIBLE, valor_original=row["categoria_raw"],
                        valor_sugerido=catalog.display_names.get(match.canonical, match.canonical),
                        score=match.score,
                    ))
                    continue
                if kind == "ambiguous":
                    candidatos = tuple(
                        catalog.display_names.get(c, c) for c, _ in match.candidates
                    )
                    hallazgos.append(Hallazgo(
                        fila=row["numero"], campo="categoria", regla_id=rule.id,
                        severidad=Severidad.CORRECTIBLE, valor_original=row["categoria_raw"],
                        valor_sugerido=None, score=match.score, candidatos=candidatos,
                    ))
                    row["ambiguous_candidates"] = ", ".join(candidatos)
                    continue
                # no_match
                if row["categoria_norm"] == "":
                    # lo captura CATEGORY_NON_EMPTY; evitar doble conteo ruidoso
                    continue
                hallazgos.append(Hallazgo(
                    fila=row["numero"], campo="categoria", regla_id=rule.id,
                    severidad=Severidad.CRITICAL, valor_original=row["categoria_raw"],
                    valor_sugerido=None, score=match.score if match else None,
                ))
                continue

            if rule.id == "PRICE_FORMAT":
                if row["precio_raw_norm"] == "":
                    # formato vacío lo maneja otra regla? precio vacío no es parseable; S4 dice PRICE_FORMAT
                    hallazgos.append(Hallazgo(
                        fila=row["numero"], campo="precio", regla_id=rule.id,
                        severidad=rule.severity, valor_original=row["precio_raw"],
                    ))
                elif row["precio_parse_error"] is not None:
                    hallazgos.append(Hallazgo(
                        fila=row["numero"], campo="precio", regla_id=rule.id,
                        severidad=rule.severity, valor_original=row["precio_raw"],
                    ))
                continue

            if rule.id == "PRICE_POSITIVE":
                if row["precio"] is not None and row["precio"] <= 0:
                    hallazgos.append(Hallazgo(
                        fila=row["numero"], campo="precio", regla_id=rule.id,
                        severidad=rule.severity, valor_original=row["precio_raw"],
                    ))
                continue

            if rule.id == "PRICE_CONFLICT":
                if row["has_price_conflict"]:
                    hallazgos.append(Hallazgo(
                        fila=row["numero"], campo="fila", regla_id=rule.id,
                        severidad=rule.severity, valor_original=row["producto_raw"],
                    ))
                continue

            if not rule.check(row):
                hallazgos.append(Hallazgo(
                    fila=row["numero"], campo=rule.field, regla_id=rule.id,
                    severidad=rule.severity, valor_original=str(row.get(f"{rule.field}_raw", row.get(rule.field, ""))),
                ))

        # Determinar estado
        severities = {h.severidad for h in hallazgos}
        if Severidad.CRITICAL in severities:
            estado = Estado.RECHAZADO
        elif Severidad.CORRECTIBLE in severities:
            estado = Estado.SUGERIDO
        else:
            estado = Estado.APROBADO

        veredicto = Veredicto(fila=row["numero"], estado=estado, hallazgos=tuple(hallazgos))
        verdicts.append(veredicto)
        records.append({"row": row, "verdict": veredicto, "discarded": False})

    summary = {
        "total_rows": len(processed),
        "aprobados": sum(1 for r in records if not r["discarded"] and r["verdict"].estado == Estado.APROBADO),
        "sugeridos": sum(1 for r in records if not r["discarded"] and r["verdict"].estado == Estado.SUGERIDO),
        "rechazados": sum(1 for r in records if not r["discarded"] and r["verdict"].estado == Estado.RECHAZADO),
        "descartados": discarded,
        "avisos_lectura": list(lectura.avisos),
    }

    result = {"summary": summary, "records": records, "verdicts": verdicts}
    write_outputs(supplier_path, output_dir, records, summary)
    return result
