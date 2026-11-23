from dataguard.engine import validate


def test_validate_produces_three_output_files(tmp_path):
    result = validate(
        "tests/fixtures/sucio.xlsx",
        "config/proveedores/ejemplo.yaml",
        output_dir=tmp_path,
    )

    assert (tmp_path / "sucio_validos.xlsx").exists()
    assert (tmp_path / "sucio_devolucion.xlsx").exists()
    assert (tmp_path / "sucio_resultado.json").exists()
    assert result["summary"]["total_rows"] == 14
