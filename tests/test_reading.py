from openpyxl import Workbook
import pytest

from dataguard.reading import read_supplier


def _make_fixture(path, *, sheet="ListaPrecios"):
    book = Workbook()
    sheet_obj = book.active
    sheet_obj.title = sheet
    sheet_obj.append(["LISTA DE PRECIOS - PROVEEDOR EJEMPLO S.A.", None, None])
    sheet_obj.append(["Vigencia: 2026-11-01", None, None])
    sheet_obj.append(["productos", "categoria", "precio"])
    sheet_obj.append(["  PEGAMENTO BLANCO  ", "  ADHESIVOS ", "1.234,56"])
    sheet_obj.append([None, "Papel", "100,00"])
    book.save(path)


def test_title_rows_are_skipped_and_physical_numbers_are_kept(tmp_path):
    path = tmp_path / "sucio.xlsx"
    _make_fixture(path)

    lectura = read_supplier(path, header_row=3, sheet="ListaPrecios")

    assert [numero for numero, _ in lectura.filas] == [4, 5]
    assert lectura.filas[0][1] == {
        "producto": "  PEGAMENTO BLANCO  ",
        "categoria": "  ADHESIVOS ",
        "precio": "1.234,56",
    }
    assert lectura.filas[1][1]["producto"] == ""


def test_custom_column_mapping(tmp_path):
    path = tmp_path / "sucio.xlsx"
    _make_fixture(path)

    lectura = read_supplier(
        path,
        header_row=3,
        sheet="ListaPrecios",
        column_map={"producto": "productos", "categoria": "categoria", "precio": "precio"},
    )

    assert lectura.filas[0][1]["precio"] == "1.234,56"


def test_missing_column_names_are_explicit(tmp_path):
    path = tmp_path / "sucio.xlsx"
    _make_fixture(path)

    with pytest.raises(ValueError, match="precio_unitario"):
        read_supplier(
            path,
            header_row=3,
            sheet="ListaPrecios",
            column_map={"producto": "productos", "categoria": "categoria", "precio": "precio_unitario"},
        )


def test_uncached_formula_is_reported_as_warning(tmp_path):
    path = tmp_path / "sucio.xlsx"
    _make_fixture(path)
    from openpyxl import load_workbook

    book = load_workbook(path)
    book["ListaPrecios"]["C4"] = "=1+1"
    book.save(path)

    lectura = read_supplier(path, header_row=3, sheet="ListaPrecios")

    assert lectura.filas[0][1]["precio"] is None
    assert any("C4" in aviso for aviso in lectura.avisos)
