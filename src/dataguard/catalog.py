from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from dataguard.normalization import normalize


@dataclass(frozen=True)
class Catalog:
    categories: frozenset[str]
    aliases: dict[str, str]
    display_names: dict[str, str]


def load_catalog(
    path: str | Path,
    *,
    sheet: str | int = 0,
    column_map: dict[str, str] | None = None,
) -> Catalog:
    """Carga el catálogo de la PYME y lo normaliza con la misma función."""
    mapping = dict(column_map or {"categoria": "categoria", "alias": "alias"})
    frame = pd.read_excel(
        Path(path),
        sheet_name=sheet,
        dtype=str,
        keep_default_na=False,
        na_values=[],
        engine="openpyxl",
    )
    missing = [source for source in mapping.values() if source not in frame.columns]
    if missing:
        raise ValueError(f"Faltan columnas en el catálogo: {', '.join(missing)}")

    categories: set[str] = set()
    aliases: dict[str, str] = {}
    display_names: dict[str, str] = {}

    for _, row in frame.iterrows():
        category_raw = str(row[mapping["categoria"]])
        alias_raw = str(row[mapping["alias"]])
        category_norm = normalize(category_raw, "match")
        alias_norm = normalize(alias_raw, "match")
        if category_norm == "":
            continue
        categories.add(category_norm)
        display_names.setdefault(category_norm, normalize(category_raw, "display"))
        if alias_norm != "":
            aliases[alias_norm] = category_norm

    # La categoría oficial también matchea por sí misma.
    for category in categories:
        aliases.setdefault(category, category)

    return Catalog(
        categories=frozenset(categories),
        aliases=aliases,
        display_names=display_names,
    )
