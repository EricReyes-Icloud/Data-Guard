import csv
import json

from openpyxl import load_workbook

from dataguard.engine import validate

FIXTURE = "tests/fixtures/sucio.xlsx"
CONFIG = "config/proveedores/ejemplo.yaml"
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


def _generate(tmp_path):
    validate(FIXTURE, CONFIG, output_dir=tmp_path)
    payload = json.loads((tmp_path / "sucio_resultado.json").read_text(encoding="utf-8"))
    with (tmp_path / "sucio_resultado.csv").open(encoding="utf-8", newline="") as fh:
        csv_rows = list(csv.DictReader(fh))
    return payload, csv_rows


def test_csv_is_a_flat_projection_of_the_json_contract(tmp_path):
    payload, csv_rows = _generate(tmp_path)

    assert list(csv_rows[0].keys()) == CSV_COLUMNS
    expected = sum(max(1, len(row["hallazgos"])) for row in payload["rows"])
    assert len(csv_rows) == expected

    entry = next(
        row for row in csv_rows
        if row["fila"] == "7" and row["regla_id"] == "CATEGORY_IN_CATALOG"
    )
    assert entry["estado"] == "sugerido"
    assert entry["valor_sugerido"] == ""
    assert json.loads(entry["candidatos"]) == ["Cemento", "Cementos"]


def test_json_publishes_hygiene_trace(tmp_path):
    payload, _ = _generate(tmp_path)

    fila_4 = next(row for row in payload["rows"] if row["fila"] == 4)
    assert isinstance(fila_4["higiene"], list)
    assert "trim" in fila_4["higiene"]


def test_devolucion_lists_ambiguous_candidates_without_a_correction(tmp_path):
    _generate(tmp_path)
    wb = load_workbook(tmp_path / "sucio_devolucion.xlsx", data_only=True)
    rows = list(wb["Devolucion"].values)
    header = rows[0]
    target = next(row for row in rows[1:] if row[0] == 7)

    assert header == (
        "fila", "campo", "valor_original", "valor_sugerido", "motivo", "regla_id", "score",
    )
    suggestion = target[header.index("valor_sugerido")]
    motivo = target[header.index("motivo")]
    assert suggestion in (None, "")
    assert "Cemento" in motivo and "Cementos" in motivo
