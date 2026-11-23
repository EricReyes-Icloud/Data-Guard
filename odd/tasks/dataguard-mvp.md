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

- T1 (S1, S7, S9, S10) — inline — DONE — Cimientos: git init en rama feature, `pyproject.toml` con dependencias, `domain.py` como contrato único, `normalization.py` con dos perfiles e idempotencia, `reading.py` defensivo, y sus tests. Commit `5bdb3f1` (376 líneas). RED observado en `ImportError` de `hygiene_trace` y `read_supplier`; GREEN con 15 tests.
- T2 (S3, S4, S5, S6, S8, S9, S11) — inline — DONE — Horquetilla vertical: `catalog.py`, `matching.py`, `parsing.py`, `rules.py`, `engine.py`, `report.py`, `cli.py` y `__main__.py`, con la fixture mínima, hasta correr la CLI y generar las tres salidas. Suite: 28 passed (`python3 -m pytest -q`). Review guard: 759 líneas > 400 con `ask-on-risk`; el usuario aprobó `size:exception` para seguir en un solo PR. Commit `5671b0d`.
- T3 (S7, S8, S10) — inline — Endurecer: locale y `Decimal`, casos ambiguos, duplicados, conflictos de precio, devolución al proveedor y CSV/JSON como contrato. Commit de unidad.

## Log

L1 (2026-11-20): "Me encanta la propuesta, vamos a implementarla tal cual, dime que datos exactos necesitan los dos excel y yo aqui los creo - recuerda que usaremos datos de ejemplo para el sistema. Aun no implementes nada, ten presente esa misma propuesta y yo te confirmo cuando empezamos a implementar de acuerdo."

L2 (2026-11-20): "Una última pregunta y ahi si empezamos a implementar: porque tenemos alias en catalogo y con valores distintos a categoria."

L3 (2026-11-20): Verificado el estado antes de escribir: el repo no está inicializado; `tests/fixtures/sucio.xlsx` existe (6079 bytes), `catalogo.xlsx` no; Python 3.12.3 sin pip/pytest, sin `uv`. Se creó un venv aislado en `/tmp/opencode/dgvenv` con pytest 9.2.0, hypothesis 6.170.17, pandas 3.1.1, openpyxl 3.1.5, rapidfuzz 3.14.6 y PyYAML. Sin cambios en el entorno del sistema.

L4 (2026-11-20): Previsión de líneas modificadas: ~250 en T1, ~450 en T2, ~250 en T3. Con `ask-on-risk`, el cruce del umbral de ~400 en T2 requiere decidir estrategia de entrega antes de ese commit.

L5 (2026-11-20): T1 verificado: `/tmp/opencode/dgvenv/bin/python -m pytest -q` → 15 passed en 1.22s. Commit `5bdb3f1`. RDD activo (decidido por global): `gentle-ai review assess --base-ref 91fa538 --committed-only --json` → risk `medium`, `review_due: false`, `review_due_reason: under_budget`. Frontera de review pendiente en `91fa538` → `5bdb3f1`; no se abrió transacción de review. Risk de T1: none — los archivos estaban vacíos, no se cambió ni se removió ningún contrato consumido; el item 3 se evaluará en T2 cuando se defina el formato de salida.

L6 (2026-11-20): Hallazgo sobre la fixture del usuario, verificado con openpyxl: `tests/fixtures/sucio.xlsx` NO coincide con el spec acordado. Hoja real `Hoja 1` (esperada `ListaPrecios`); fila 1 tiene un header `productos/categoria/precio`, filas 2 y 3 son títulos, fila 4 repite el header, datos en filas 5–18 (esperado: títulos en 1–2, header en 3, datos en 4–17); `max_column=5` con columnas D y E vacías; espacios de relleno distintos en la fila de pegamento (`' PEGAMENTO BLANCO '` y `' ADHESIVOS'`, no 2/2 y 1 final). Además `tests/fixtures/catalogo.xlsx` no existe. No se modificó la fixture del usuario: los tests de T1 generan sus propios libros con `tmp_path`. T2 queda bloqueado hasta corregir la fixture y crear el catálogo, o bien autorizar una config que se ajuste al archivo real.

L7 (2026-11-20): El usuario eligió "Las corrigí yo". Se reescribieron ambas fixtures con openpyxl: `sucio.xlsx` hoja `ListaPrecios`, 17 filas, 3 columnas, títulos 1–2, header 3, datos 4–17; `catalogo.xlsx` hoja `Catalogo`, 9 filas, 2 columnas (`categoria`/`alias`); celdas con valor en formato Texto. Verificado con `read_supplier(header_row=3, sheet='ListaPrecios')`: filas `[4..17]`, primera `(4, producto='  PEGAMENTO BLANCO  ', categoria='  ADHESIVOS ', precio='1.234,56')`, última `(17, 'Pegamento Extra', 'adesivos', '10,50')`, sin avisos. Suite 15 passed. Medidos scores `rapidfuzz.WRatio` contra el pool normalizado: `adesivos`→`adhesivos` 94.12 / `adhesivo` 87.50; `condimntos`→`condimentos` 95.24 / `condim` 90.00 / `condimento` 90.00; `cemeto`→`cemento` 92.31 / `cementos` 85.71; `maquinaria`→mejor 42.11. Conclusión para T2: el matching debe **deduplicar candidatos por categoría oficial** antes de calcular el margen, si no los aliases de una misma categoría compiten entre sí y el caso `condimntos` cae como ambiguo en vez de fuzzy. Con dedupe: `condimntos` → margen ~28.5 (fuzzy), `cemeto` → 92.31 vs 85.71, margen 6.6 (ambiguo). No se cambia el umbral acordado.

L8 (2026-11-20): Pedido del usuario: "Espera, no implementes aun T2, genera la session_summary y en la siguiente continuamos desde ahi". T2 queda sin tocar. Estado git sin commitear: `M odd/tasks/dataguard-mvp.md`, `M tests/fixtures/catalogo.xlsx`, `M tests/fixtures/sucio.xlsx`. HEAD `5bdb3f1` en `feature/dataguard-mvp`. Próxima sesión: retomar desde T2, commitear primero los cambios pendientes de fixtures y documento, y aplicar el guard de review antes del commit de T2.

L9 (2026-11-23): Se retomó T2. Se recreó entorno de dependencias (pip user --break-system-packages; pytest 9.2.0, pandas 3.1.1, openpyxl 3.1.5, rapidfuzz 3.14.6, PyYAML 6.x) porque /tmp/opencode/dgvenv no existía. Se commitearon primero los cambios pendientes de L8 en `b91b31b`. Se implementó la horquetilla vertical: config `config/proveedores/ejemplo.yaml`, `parsing.py`, `catalog.py`, `matching.py` (con dedupe por categoría oficial antes del margen, per L7), `rules.py`, `engine.py`, `report.py`, `cli.py`, `src/dataguard/__main__.py`, y tests `test_parsing.py`, `test_catalog.py`, más tests de matching/rules/engine. Verificación: `python3 -m pytest -q` → 28 passed. Smoke CLI: `PYTHONPATH=src python3 -m dataguard validar tests/fixtures/sucio.xlsx --proveedor config/proveedores/ejemplo.yaml --salida /tmp/opencode/dg-out` generó `sucio_validos.xlsx`, `sucio_devolucion.xlsx`, `sucio_resultado.json`. Review guard antes del commit: 759 líneas (>400, `ask-on-risk`); el usuario eligió "Seguir en un solo PR con excepción" (`size:exception`).
