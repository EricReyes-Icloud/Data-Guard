# DataGuard — Arquitectura y propósito de cada archivo

Mapa de la estructura aprobada en `design.md` §7, explicado módulo por módulo: qué contiene cada archivo, cuál es su responsabilidad dentro del sistema y cómo se relaciona con el resto.

## Lectura previa para quien viene de JavaScript

- `pyproject.toml` ≈ `package.json` (dependencias, metadata, entry point).
- Cada `.py` ≈ un módulo ESM. `import` cumple el mismo rol que `import`, pero sin bundler.
- `__init__.py` es lo que convierte la carpeta en un paquete importable (`from dataguard import engine`). En JS eso lo resuelve el `package.json`; en Python hace falta el archivo.
- El layout `src/` mantiene el código en `src/dataguard/` para que los tests importen el paquete **instalado** y no un archivo suelto del directorio de trabajo.

## El flujo del pipeline

El orden de ejecución define el orden real de las responsabilidades:

```
leer → normalizar → parsear → (catálogo + matching) → validar reglas → clasificar → generar salidas
```

## Los módulos (`src/dataguard/`)

### `reading.py` — Entrada defensiva

Abre el `.xlsx` en modo defensivo: todo como string (no se permite que pandas/openpyxl adivinen tipos), `header_row` configurable y `data_only=True`. Su única responsabilidad es devolver filas crudas junto con el número de fila original. No normaliza ni valida.

### `normalization.py` — Higiene determinista

Aplica NFKC, casefold, eliminación de acentos y de puntuación. Es una función pura e **idempotente** (`normalize(normalize(x)) == normalize(x)`). Devuelve el valor limpio y la lista de transformaciones aplicadas, porque BN-6 exige trazabilidad.

### `parsing.py` — Precio a `Decimal`

Convierte el precio crudo a `Decimal`. Acá vive el locale del proveedor (`1.234,56` vs `1,234.56`) y la cuantización a `0.01` con `ROUND_HALF_UP`. Si el valor no parsea, devuelve `None` en lugar de fallar: la regla `PRICE_FORMAT` decide después.

### `catalog.py` — Catálogo de la PYME

Carga el catálogo de la PYME (Excel/CSV) y lo normaliza con `normalization`, construyendo el índice de categorías y alias. Es la **fuente de verdad** (BN-2/BN-3), no una lista hardcodeada.

### `matching.py` — Escalera de matching

Implementa la escalera de `design.md` §5: exacto → alias → fuzzy (`rapidfuzz`, `WRatio ≥ 90` con margen ≥ 10) → ambiguo → sin match. Devuelve el candidato y el score. No decide severidad; eso corresponde a `rules`.

### `rules.py` — Reglas como datos

Es el corazón del diseño: reglas **como datos**, no como condicionales dispersos. Contiene los registros declarativos `Rule(id, field, severity, check, message)` y las funciones puras de verificación. El YAML del proveedor activa y parametriza cuáles corren.

### `engine.py` — Orquestación y clasificación

Orquesta el procesamiento por fila: descarta duplicados exactos (antes de validar), ejecuta las reglas activas, aplica el matching de categorías y produce un `Veredicto` (`aprobado` / `sugerido` / `rechazado`) por fila. Acá vive el modelo de dominio de `design.md` §3.

### `report.py` — Salidas

Genera las salidas de `design.md` §8: `validos.xlsx`, `devolucion.xlsx` y `resultado.json`/CSV. El Excel es la interfaz para humanos; el CSV/JSON es el **contrato** para sistemas.

### `cli.py` — Interfaz de línea de comandos

Solo interfaz: parsea argumentos (`validar <archivo> --proveedor <yaml>`), llama a `engine` y delega la escritura a `report`. Sin lógica de negocio: es el punto de entrada.

### `__init__.py` — Marcador de paquete

Vacío, o como máximo expone `__version__`. No debe contener lógica.

## El resto de la estructura

### `config/proveedores/ejemplo.yaml`

Configuración que hace que un segundo proveedor sea configuración y no un segundo script: mapeo de columnas, locale, `header_row`, ruta del catálogo, reglas activas y sus parámetros.

### `tests/test_normalization.py`

Property-based testing con `hypothesis` sobre la idempotencia. Es el test más barato y el que más defectos evita.

### `tests/test_rules.py`

Cada regla como función pura: se le pasa un valor y se espera un `Hallazgo` o `None`. Sin Excel ni I/O.

### `tests/test_matching.py`

La escalera de matching completa, con los casos ambiguo y sin match explícitos.

### `tests/test_engine.py`

Golden files end-to-end: `fixtures/sucio.xlsx` + `catalogo.xlsx` hacia la salida esperada versionada.

### `tests/fixtures/`

Archivos sucios y salidas doradas. El corpus crece con cada proveedor nuevo.

### `pyproject.toml`

Dependencias (`openpyxl`/`pandas`, `rapidfuzz`, `pytest`, `hypothesis`), metadata y el entry point del CLI para exponer `dataguard` como comando.

## Regla de dependencias

Las dependencias van en un solo sentido:

```
cli → engine → {reading, normalization, parsing, catalog, matching, rules} → report
```

Ningún módulo de dominio importa `cli` ni `report`. Una importación "hacia arriba" indica un problema de diseño, no una particularidad de Python.
