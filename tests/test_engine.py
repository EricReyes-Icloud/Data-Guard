from pathlib import Path

from dataguard.engine import validate

FIXTURE = "tests/fixtures/sucio.xlsx"
CONFIG = "config/proveedores/ejemplo.yaml"
GOLDEN = Path("tests/fixtures/golden")


def test_validate_produces_four_output_files(tmp_path):
    result = validate(
        "tests/fixtures/sucio.xlsx",
        "config/proveedores/ejemplo.yaml",
        output_dir=tmp_path,
    )

    assert (tmp_path / "sucio_validos.xlsx").exists()
    assert (tmp_path / "sucio_devolucion.xlsx").exists()
    assert (tmp_path / "sucio_resultado.json").exists()
    assert (tmp_path / "sucio_resultado.csv").exists()
    assert result["summary"]["total_rows"] == 14


def test_ambiguous_category_has_no_suggested_value(tmp_path):
    result = validate(FIXTURE, CONFIG, output_dir=tmp_path)
    fila_7 = next(r for r in result["records"] if r["row"]["numero"] == 7)
    hallazgo = next(
        h for h in fila_7["verdict"].hallazgos
        if h.regla_id == "CATEGORY_IN_CATALOG"
    )

    assert hallazgo.valor_sugerido is None
    assert hallazgo.candidatos == ("Cemento", "Cementos")


def test_golden_outputs_match_generated_contracts(tmp_path):
    validate(FIXTURE, CONFIG, output_dir=tmp_path)

    assert (tmp_path / "sucio_resultado.json").read_text(encoding="utf-8") == (
        GOLDEN / "sucio_resultado.json"
    ).read_text(encoding="utf-8")
    assert (tmp_path / "sucio_resultado.csv").read_text(encoding="utf-8") == (
        GOLDEN / "sucio_resultado.csv"
    ).read_text(encoding="utf-8")
