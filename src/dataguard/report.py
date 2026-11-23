import json
from pathlib import Path

from openpyxl import Workbook

from dataguard.domain import Estado
from dataguard.rules import RULES


def _safe_name(stem: str) -> str:
    return stem.replace(" ", "_")


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
            motivo = RULES.get(h.regla_id).message if h.regla_id in RULES else h.regla_id
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


def _write_json(path: Path, records: list[dict], summary: dict) -> None:
    rows = []
    for rec in records:
        row = rec["row"]
        verdict = rec["verdict"]
        rows.append({
            "fila": row["numero"],
            "estado": verdict.estado.value,
            "descartada": rec["discarded"],
            "producto": row["producto"],
            "categoria": row.get("categoria_canonica", row["categoria"]),
            "categoria_original": row["categoria"],
            "precio": format(row["precio"], "0.2f") if row["precio"] is not None else None,
            "hallazgos": [
                {
                    "campo": h.campo,
                    "regla_id": h.regla_id,
                    "severidad": h.severidad.value,
                    "valor_original": h.valor_original,
                    "valor_sugerido": h.valor_sugerido,
                    "score": h.score,
                }
                for h in verdict.hallazgos
            ],
        })
    payload = {"summary": summary, "rows": rows}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_outputs(supplier_path: Path, output_dir: Path, records: list[dict], summary: dict) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = _safe_name(Path(supplier_path).stem)
    validos = output_dir / f"{stem}_validos.xlsx"
    devolucion = output_dir / f"{stem}_devolucion.xlsx"
    resultado = output_dir / f"{stem}_resultado.json"
    _write_validos(validos, records)
    _write_devolucion(devolucion, records)
    _write_json(resultado, records, summary)
    return {"validos": str(validos), "devolucion": str(devolucion), "resultado": str(resultado)}
