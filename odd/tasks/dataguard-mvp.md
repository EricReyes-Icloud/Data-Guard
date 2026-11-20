# DataGuard MVP — walking skeleton y endurecimiento

Rama: `feature/dataguard-mvp`. Estrategia de entrega: `ask-on-risk`. Runner: `/tmp/opencode/dgvenv/bin/python -m pytest`.

Objetivo: implementar la propuesta senior aceptada — contratos, horquetilla vertical y endurecimiento — con datos de ejemplo ficticios creados por el usuario.

## Specs

S1. "Me encanta la propuesta, vamos a implementarla tal cual, dime que datos exactos necesitan los dos excel y yo aqui los creo - recuerda que usaremos datos de ejemplo para el sistema. Aun no implementes nada, ten presente esa misma propuesta y yo te confirmo cuando empezamos a implementar de acuerdo." — la secuencia acordada es contratos → horquetilla vertical → endurecer; el inicio está supeditado a la confirmación del usuario.

S2. "Una última pregunta y ahi si empezamos a implementar: porque tenemos alias en catalogo y con valores distintos a categoria." — confirmación de arranque de la implementación.

S3. "solo con las columnas productos, categoria y precio, verdad." — el Excel del proveedor no lleva columna `fila` ni columnas adicionales. `design.md` §2 coincide.

S4. "no debo excluirlos del excel, al contratio los prevalecemos para que dataGuard haga su trabajo" — las filas 1 y 2 de título se conservan; `header_row: 3` las saltea.

S5. "Los que dices (vacío), los dejo vacios o agrego ese texto" — respuesta: las celdas marcadas como vacío quedan sin ningún carácter; `N/A` y `-` son texto literal.

S6. "porque tenemos alias en catalogo y con valores distintos a categoria." — los alias son equivalencias curadas por humanos: dan `aprobado` con traza, no `sugerido`; el fuzzy es el último recurso y nunca se aplica.

S7. De `docs/design.md` §2 y §3 (diseño cerrado, confirmado 2026-11-11): lectura defensiva (`dtype=str`, `keep_default_na=False`, `na_values=[]`, `header_row` configurable, `data_only=True`), un solo normalizador para proveedor y catálogo, dinero con `Decimal`, y modelo de dominio `Estado`, `Severidad`, `Fila`, `Hallazgo`, `Veredicto`.

S8. De `docs/design.md` §4 y §5 (diseño cerrado): reglas como datos activadas por YAML, y escalera de matching normalización → exacto → alias → fuzzy con `WRatio ≥ 90` y margen ≥ 10 → ambiguo → sin match.

S9. De `docs/design.md` §6 y §7: CLI `python -m dataguard validar <archivo-proveedor> --proveedor config/proveedores/<nombre>.yaml`, y salidas `validos.xlsx`, `devolucion.xlsx` y `resultado.json`. Requiere `src/dataguard/__main__.py` y un `domain.py` como contrato único (huecos detectados el 2026-11-20).

S10. De `docs/design.md` §8 y §9: hoja de devolución con `fila`, `campo`, `valor_original`, `valor_sugerido`, `motivo`, `regla_id`, `score`; CSV/JSON como contrato estable; golden files e idempotencia de normalización.

S11. Supuesto explícito: `tests/fixtures/sucio.xlsx` ya existe; `tests/fixtures/catalogo.xlsx` todavía no está en disco al iniciar T1, y se necesita para T2.

## Tasks

- T1 (S1, S7, S9, S10) — inline — Cimientos: git init en rama feature, `pyproject.toml` con dependencias, `domain.py` como contrato único, `normalization.py` con dos perfiles e idempotencia, `reading.py` defensivo, y sus tests. Commit de unidad.
- T2 (S3, S4, S5, S6, S8, S9, S11) — inline — Horquetilla vertical: `catalog.py`, `matching.py`, `rules.py`, `engine.py`, `report.py`, `cli.py` y `__main__.py`, con la fixture mínima, hasta correr la CLI y generar las tres salidas. Commit de unidad.
- T3 (S7, S8, S10) — inline — Endurecer: locale y `Decimal`, casos ambiguos, duplicados, conflictos de precio, devolución al proveedor y CSV/JSON como contrato. Commit de unidad.

## Log

L1 (2026-11-20): "Me encanta la propuesta, vamos a implementarla tal cual, dime que datos exactos necesitan los dos excel y yo aqui los creo - recuerda que usaremos datos de ejemplo para el sistema. Aun no implementes nada, ten presente esa misma propuesta y yo te confirmo cuando empezamos a implementar de acuerdo."

L2 (2026-11-20): "Una última pregunta y ahi si empezamos a implementar: porque tenemos alias en catalogo y con valores distintos a categoria."

L3 (2026-11-20): Verificado el estado antes de escribir: el repo no está inicializado; `tests/fixtures/sucio.xlsx` existe (6079 bytes), `catalogo.xlsx` no; Python 3.12.3 sin pip/pytest, sin `uv`. Se creó un venv aislado en `/tmp/opencode/dgvenv` con pytest 9.2.0, hypothesis 6.170.17, pandas 3.1.1, openpyxl 3.1.5, rapidfuzz 3.14.6 y PyYAML. Sin cambios en el entorno del sistema.

L4 (2026-11-20): Previsión de líneas modificadas: ~250 en T1, ~450 en T2, ~250 en T3. Con `ask-on-risk`, el cruce del umbral de ~400 en T2 requiere decidir estrategia de entrega antes de ese commit.
