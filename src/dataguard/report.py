import csv
import json
from pathlib import Path

from openpyxl import Workbook

from dataguard.domain import Estado
from dataguard.rules import RULES

CSV_COLUMNS = [
    "fila",
    "estado",
    "descartada",
    "producto",
    "categoria",
    "categoria_original",
    "precio",
    "higiene",
    "campo",
    "regla_id",
    "severidad",
    "valor_original",
    "valor_sugerido",
    "score",
    "candidatos",
]
ROW_COLUMNS = CSV_COLUMNS[:8]
FINDING_COLUMNS = CSV_COLUMNS[8:]


def _safe_name(stem: str) -> str:
    return stem.replace(" ", "_")


def _encode_list(values: list) -> str:
    return json.dumps(values, ensure_ascii=False, separators=(",", ":"))


def _contract_rows(records: list[dict]) -> list[dict]:
    """Un registro por hallazgo; las filas sin hallazgos también comparecen."""
    rows: list[dict] = []
    for rec in records:
        row = rec["row"]
        verdict = rec["verdict"]
        base = {
            "fila": row["numero"],
            "estado": verdict.estado.value,
            "descartada": rec["discarded"],
            "producto": row["producto"],
            "categoria": row.get("categoria_canonica", row["categoria"]),
            "categoria_original": row["categoria"],
            "precio": format(row["precio"], "0.2f") if row["precio"] is not None else None,
            "higiene": list(row.get("higiene", ())),
        }
        if not verdict.hallazgos:
            rows.append({**base, "campo": "", "regla_id": "", "severidad": "",
                         "valor_original": "", "valor_sugerido": None,
                         "score": None, "candidatos": []})
            continue
        for h in verdict.hallazgos:
            rows.append({
                **base,
                "campo": h.campo,
                "regla_id": h.regla_id,
                "severidad": h.severidad.value,
                "valor_original": h.valor_original,
                "valor_sugerido": h.valor_sugerido,
                "score": h.score,
                "candidatos": list(h.candidatos),
            })
    return rows


def _write_validos(path: Path, records: list[dict]) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Validos"
    ws.append(["fila", "productos", "categoria", "precio"])
    for rec in records:
        if rec["discarded"]:
            continue
        verdict = rec["verdict"]
        row = rec["row"]
        if verdict.estado != Estado.APROBADO:
            continue
        precio = row["precio"]
        categoria = row.get("categoria_canonica", row["categoria"])
        ws.append([
            row["numero"],
            row["producto"],
            categoria,
            format(precio, "0.2f") if precio is not None else "",
        ])
    wb.save(path)


def _write_devolucion(path: Path, records: list[dict]) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Devolucion"
    ws.append(["fila", "campo", "valor_original", "valor_sugerido", "motivo", "regla_id", "score"])
    for rec in records:
        verdict = rec["verdict"]
        if verdict.estado == Estado.APROBADO:
            continue
        for h in verdict.hallazgos:
            motivo = RULES[h.regla_id].message if h.regla_id in RULES else h.regla_id
            if h.candidatos:
                motivo = f"{motivo}. Candidatos: {', '.join(h.candidatos)}"
            ws.append([
                h.fila,
                h.campo,
                h.valor_original,
                h.valor_sugerido if h.valor_sugerido is not None else "",
                motivo,
                h.regla_id,
                h.score if h.score is not None else "",
            ])
    wb.save(path)


def _write_json(path: Path, contract_rows: list[dict], summary: dict) -> None:
    by_fila: dict[int, dict] = {}
    rows: list[dict] = []
    for entry in contract_rows:
        fila = entry["fila"]
        if fila not in by_fila:
            item = {column: entry[column] for column in ROW_COLUMNS}
            item["hallazgos"] = []
            by_fila[fila] = item
            rows.append(item)
        if entry["regla_id"]:
            by_fila[fila]["hallazgos"].append(
                {column: entry[column] for column in FINDING_COLUMNS}
            )

    payload = {"summary": summary, "rows": rows}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_csv(path: Path, contract_rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for entry in contract_rows:
            writer.writerow({
                **{column: entry[column] for column in ROW_COLUMNS if column not in {"higiene", "descartada"}},
                "descartada": "true" if entry["descartada"] else "false",
                "higiene": _encode_list(entry["higiene"]),
                "campo": entry["campo"],
                "regla_id": entry["regla_id"],
                "severidad": entry["severidad"],
                "valor_original": entry["valor_original"],
                "valor_sugerido": entry["valor_sugerido"] or "",
                "score": "" if entry["score"] is None else entry["score"],
                "candidatos": _encode_list(entry["candidatos"]),
            })


def write_outputs(supplier_path: Path, output_dir: Path, records: list[dict], summary: dict) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = _safe_name(Path(supplier_path).stem)
    validos = output_dir / f"{stem}_validos.xlsx"
    devolucion = output_dir / f"{stem}_devolucion.xlsx"
    resultado_json = output_dir / f"{stem}_resultado.json"
    resultado_csv = output_dir / f"{stem}_resultado.csv"
    contract_rows = _contract_rows(records)
    _write_validos(validos, records)
    _write_devolucion(devolucion, records)
    _write_json(resultado_json, contract_rows, summary)
    _write_csv(resultado_csv, contract_rows)
    return {
        "validos": str(validos),
        "devolucion": str(devolucion),
        "resultado": str(resultado_json),
        "resultado_csv": str(resultado_csv),
    }
