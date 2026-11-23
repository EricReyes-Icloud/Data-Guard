from openpyxl import Workbook

from dataguard.catalog import load_catalog


def _make_catalog(path):
    book = Workbook()
    ws = book.active
    ws.title = "Catalogo"
    ws.append(["categoria", "alias"])
    ws.append(["Adhesivos", "adesivos"])
    ws.append(["Adhesivos", "adhesivo"])
    ws.append(["Condimentos", "Condim."])
    book.save(path)


def test_load_catalog_normalizes_categories_and_aliases(tmp_path):
    path = tmp_path / "catalogo.xlsx"
    _make_catalog(path)

    catalog = load_catalog(path, sheet="Catalogo")

    assert "adhesivos" in catalog.categories
    assert catalog.aliases["adesivos"] == "adhesivos"
    assert catalog.aliases["adhesivo"] == "adhesivos"
    assert catalog.aliases["condim"] == "condimentos"
