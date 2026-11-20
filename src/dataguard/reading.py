from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook

DEFAULT_COLUMN_MAP = {
    "producto": "productos",
    "categoria": "categoria",
    "precio": "precio",
}


@dataclass(frozen=True)
class Lectura:
    filas: tuple[tuple[int, dict[str, str | None]], ...]
    avisos: tuple[str, ...]


def _uncached_formulas(path, sheet, header_row, column_map):
    formulas = load_workbook(path, data_only=False)[sheet]
    values = load_workbook(path, data_only=True)[sheet]

    header_columns = {
        str(cell.value): cell.column_letter
        for cell in values[header_row]
        if cell.value is not None
    }
    coordinates: dict[tuple[str, int], str] = {}
    avisos: list[str] = []

    for field, source in column_map.items():
        letter = header_columns.get(source)
        if letter is None:
            continue
        for row_number in range(header_row + 1, values.max_row + 1):
            coordinate = f"{letter}{row_number}"
            raw = formulas[coordinate].value
            cached = values[coordinate].value
            if isinstance(raw, str) and raw.startswith("=") and cached is None:
                coordinates[(field, row_number)] = coordinate
                avisos.append(
                    f"Fórmula sin calcular en {sheet}!{coordinate}: "
                    "el valor se reporta como vacío y debe revisarse."
                )

    return coordinates, tuple(avisos)


def read_supplier(
    path: str | Path,
    *,
    header_row: int = 1,
    sheet: str = 0,
    column_map: dict[str, str] | None = None,
) -> Lectura:
    """Lee el Excel del proveedor sin interpretar ni corregir ningún valor.

    ``header_row`` es 1-based, como aparece en la configuración YAML. Los
    números de fila devueltos son los físicos del libro, no posiciones
    relativas a los datos.
    """
    mapping = dict(column_map or DEFAULT_COLUMN_MAP)
    path = Path(path)

    frame = pd.read_excel(
        path,
        sheet_name=sheet,
        header=header_row - 1,
        dtype=str,
        keep_default_na=False,
        na_values=[],
        engine="openpyxl",
    )
    missing = [source for source in mapping.values() if source not in frame.columns]
    if missing:
        raise ValueError(f"Faltan columnas en el archivo del proveedor: {', '.join(missing)}")

    coordinates: dict[tuple[str, int], str] = {}
    avisos: tuple[str, ...] = ()
    if isinstance(sheet, str):
        coordinates, avisos = _uncached_formulas(path, sheet, header_row, mapping)

    filas: list[tuple[int, dict[str, str | None]]] = []
    for position, row in frame.iterrows():
        row_number = header_row + 1 + int(position)
        values: dict[str, str | None] = {}
        for field, source in mapping.items():
            if (field, row_number) in coordinates:
                values[field] = None
                continue
            raw = row[source]
            values[field] = "" if pd.isna(raw) else str(raw)
        filas.append((row_number, values))

    return Lectura(filas=tuple(filas), avisos=avisos)
