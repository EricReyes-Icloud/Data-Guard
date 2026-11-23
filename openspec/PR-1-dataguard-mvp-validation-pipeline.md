## Description

DataGuard began as a skeleton: the design docs and empty modules described a validation flow for supplier price spreadsheets, but there was no executable pipeline. Supplier files contain title rows, padded and placeholder text, category aliases, malformed prices, duplicate rows and conflicting prices, so importing them as-is risks reinterpreting values. This PR implements the agreed sequence — contracts, a vertical slice, then hardening — so every row can be classified as `aprobado`, `sugerido` or `rechazado` and returned to the supplier with a traceable reason.

The cause of unsafe validation was that raw Excel values cannot be treated as clean data: pandas coerces strings, header rows are not fixed, and a single aggressive normalization would destroy the values that must be shown back to the supplier. The branch therefore separates two normalization profiles (`display` and `match`), reads the workbook defensively, keeps money in `Decimal`, and defines rules as data activated through `reglas_activas` in `config/proveedores/ejemplo.yaml`. Curated aliases resolve to `aprobado` with a trace; fuzzy matches only produce a correction, and ambiguous matches publish candidates without inventing a value.

The vertical slice runs from `read_supplier` through catalog loading, category matching, price parsing, rule evaluation, verdict assembly and report writing, exposed through `python -m dataguard validar`. Hardening tightened `parse_price` for locale correctness and turned the JSON/CSV output into one shared contract backed by golden files, so the CLI can be regression-checked byte for byte.

## Changes Made

**Features**

- `src/dataguard/domain.py` — added the frozen contracts `Estado`, `Severidad`, `Fila`, `Hallazgo`, `Veredicto` and `Rule`, including `candidatos` on `Hallazgo`.
- `src/dataguard/normalization.py` — added `normalize` with `display` and `match` profiles plus `hygiene_trace` for placeholder, accent, whitespace and punctuation changes.
- `src/dataguard/reading.py` — added `read_supplier` with `dtype=str`, `keep_default_na=False`, `na_values=[]`, a configurable 1-based `header_row`, physical row numbers, and warnings for formulas without cached values.
- `src/dataguard/catalog.py` — added `load_catalog`, which normalizes `categoria` and `alias` with the same profiles and registers each official category as its own alias.
- `src/dataguard/matching.py` — added the exact/alias/fuzzy ladder using `WRatio >= 90` with a margin of at least 10, deduplicated by official category before the margin is applied, with `ambiguous` and `no_match` results.
- `src/dataguard/parsing.py` — added locale-aware `parse_price` for `es_AR` and `en_US`, quantized with `Decimal` and `ROUND_HALF_UP`.
- `src/dataguard/rules.py` — added seven named `Rule` entries activated through `reglas_activas`.
- `src/dataguard/engine.py` — added `validate` to wire reading, catalog loading, rules, duplicate detection, price conflicts, verdicts and the summary; ambiguous categories become `sugerido` with `valor_sugerido=None` and `candidatos`.
- `src/dataguard/report.py` — added `<stem>_validos.xlsx`, `<stem>_devolucion.xlsx`, `<stem>_resultado.json` and `<stem>_resultado.csv` output from a single contract, with `higiene` and `candidatos` published in JSON and CSV.
- `src/dataguard/cli.py` and `src/dataguard/__main__.py` — added the `validar` subcommand with `--proveedor` and optional `--salida`, printing the JSON summary.

**Bug fixes and hardening**

- `src/dataguard/parsing.py` — rejects non-finite prices and malformed thousands grouping instead of silently accepting them.
- `src/dataguard/engine.py` — limits `higiene` to product and category, leaving price validation to locale parsing.
- `src/dataguard/report.py` — names candidates in the `motivo` of `Devolucion` without writing a fabricated `valor_sugerido`, and projects the same fields into the flat CSV.

**Configuration and fixtures**

- `config/proveedores/ejemplo.yaml` — added the example provider with `header_row: 3`, `sheet: ListaPrecios`, `column_map`, `locale: es_AR`, `catalogo`, `catalog_sheet`, `catalog_column_map` and `reglas_activas`.
- `tests/fixtures/sucio.xlsx` and `tests/fixtures/catalogo.xlsx` — rewrote the fixtures to the agreed layout: `ListaPrecios` with titles in rows 1–2, header in row 3 and data in rows 4–17, plus `Catalogo` with `categoria` and `alias`.

**Tests and golden files**

- `tests/test_normalization.py`, `tests/test_reading.py`, `tests/test_catalog.py`, `tests/test_matching.py`, `tests/test_parsing.py`, `tests/test_rules.py`, `tests/test_engine.py` and `tests/test_report.py` — added coverage across all three stages; 36 tests pass at HEAD.
- `tests/fixtures/golden/sucio_resultado.json` and `tests/fixtures/golden/sucio_resultado.csv` — added golden outputs generated from two identical runs.

**Dev tooling**

- `pyproject.toml` — configured the setuptools `src` layout, runtime and dev dependencies, and pytest `pythonpath` and `testpaths`.
- `.gitignore` — ignored Python bytecode, pytest cache, virtualenvs and build artifacts.

**Documentation**

- `odd/tasks/dataguard-mvp.md` — recorded the accepted specs S1–S11, task status and verification evidence, including the L10 differential check.

## Impact

- Approved rows are written to `<stem>_validos.xlsx`, while non-approved rows appear in `<stem>_devolucion.xlsx` with `fila`, `campo`, `valor_original`, `valor_sugerido`, `motivo`, `regla_id` and `score`. Exact and curated alias matches stay `aprobado`, fuzzy matches become `sugerido`, critical findings become `rechazado`, and exact duplicates are counted as `descartados`.
- The JSON contract gained `higiene` and `candidatos`, ambiguous rows now carry `valor_sugerido: null`, and the flat CSV mirrors the JSON fields. The differential check against `3339f90` found no change in CLI stdout, stderr, exit code or the `Validos` sheet; the only intended changes were the row 7 `motivo` in `Devolucion` and the JSON additions. No external consumers of the contract exist in v1, and the base modules were empty, so no consumed contract was removed.
- Developers can run the full pipeline from the CLI and compare outputs against checked-in goldens. The T2 slice exceeded the 400-line review threshold at 759 lines; the user approved `size:exception` to keep the work in one PR.
- Known caveat: a numeric Excel price serialized as `1234.56` is rejected under `es_AR` as a malformed thousands grouping instead of being silently misread. Supplier prices must use text-formatted values such as `1.234,56`.

## Notes

- Verification recorded in `odd/tasks/dataguard-mvp.md` L10: RED was observed in 7 new tests, then `python3 -m pytest -q` reported 36 passed; earlier stages recorded 15 and 28 passed.
- Golden JSON and CSV were byte-identical across two runs. The differential check against `3339f90` confirmed identical CLI stdout, stderr and exit code and an identical `Validos` sheet, with the single expected `Devolucion` change at row 7 and only additive JSON fields.
- CLI smoke command: `PYTHONPATH=src python3 -m dataguard validar tests/fixtures/sucio.xlsx --proveedor config/proveedores/ejemplo.yaml --salida /tmp/opencode/dg-out` generates `sucio_validos.xlsx`, `sucio_devolucion.xlsx`, `sucio_resultado.json` and, after T3, `sucio_resultado.csv`.
- No follow-up issues are recorded in `odd/tasks/dataguard-mvp.md`; the `es_AR` rejection of `1234.56` is a deliberate parsing rule, not a pending fix. This is PR content only — no PR was opened or submitted.
