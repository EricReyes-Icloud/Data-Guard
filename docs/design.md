# DataGuard — Diseño técnico cerrado

> Derivado de `summary.md` (pitch) y `principal-propose.md` (propuesta senior), con las decisiones de negocio confirmadas el 2026-11-11.
> Estado: diseño cerrado. Siguiente paso: plan de implementación.

## 1. Reglas de negocio confirmadas

| # | Regla | Origen |
|---|---|---|
| BN-1 | El proveedor entrega **un solo archivo Excel** con tres columnas: `productos`, `categoria`, `precio`. | Confirmada 2026-11-11 |
| BN-2 | **El catálogo de la PYME es la fuente de verdad** para categorías. La categoría del proveedor se compara contra el catálogo oficial que la PYME ya tiene (ej.: proveedor "adesivos" → catálogo "adhesivos"). La razón: los sistemas de la PYME importan la información nueva del proveedor y debe coincidir con su catálogo actual. | Confirmada 2026-11-11 |
| BN-3 | Una categoría desconocida **no se integra sola**. La fila se bloquea y la decisión es de la PYME: integrar el producto nuevo en su catálogo (y volver a correr) o devolver el error al proveedor. | Derivada de BN-2 |
| BN-4 | El archivo del proveedor es **inmutable**: nunca se escribe sobre el original. | Propuesta |
| BN-5 | **Nunca se auto-corrige.** Toda corrección es una sugerencia con score; la decisión final es humana. | Propuesta |
| BN-6 | La higiene (espacios, mayúsculas/minúsculas, acentos, vacíos y `"N/A"`/`"-"`) se aplica y se deja **trazada**. No es error. | Propuesta |
| BN-7 | El dinero se maneja con `Decimal`, jamás `float` (`quantize(Decimal("0.01"), ROUND_HALF_UP)`). | Propuesta |

## 2. Entrada y referencia

- **Entrada:** un `.xlsx` del proveedor con las columnas `productos`, `categoria`, `precio`.
  - Lectura defensiva: todo como string (`dtype=str`, `keep_default_na=False`, `na_values=[]`), `header_row` configurable.
  - `data_only=True` con detección de fórmulas nunca recalculadas: aviso claro, no fallo opaco.
- **Referencia:** el catálogo de categorías de la PYME, exportado de su sistema (`.xlsx` o `.csv`).
  - DataGuard **solo lo lee**: el ciclo de vida del catálogo vive en el sistema de la PYME (BN-2, BN-3).
  - Es un export más, así que también se lee defensivamente y se normaliza con la **misma función** que el archivo del proveedor — un solo normalizador, cero duplicación.
- **Configuración por proveedor** (`config/proveedores/<nombre>.yaml`): mapeo de columnas al dominio, locale de números, `header_row`, catálogo de referencia, reglas activas.

## 3. Modelo de dominio

```python
class Estado(str, Enum):
    APROBADO = "aprobado"    # pasa a la hoja limpia
    SUGERIDO = "sugerido"   # hay corrección probable; no se aplica, va a revisión
    RECHAZADO = "rechazado"  # viola una regla dura

class Severidad(str, Enum):
    CRITICAL = "critical"        # bloquea la fila
    CORRECTIBLE = "correctible" # lleva sugerencia; decisión humana
    WARNING = "warning"          # no bloquea; queda trazado

@dataclass(frozen=True)
class Fila:
    numero: int                # fila 1-based del Excel original
    producto: str              # normalizado
    categoria: str             # normalizado
    precio: Decimal | None     # None si no parsea
    higiene: tuple[str, ...]   # normalizaciones aplicadas, trazadas (BN-6)

@dataclass(frozen=True)
class Hallazgo:
    fila: int
    campo: str                 # "producto" | "categoria" | "precio" | "fila"
    regla_id: str
    severidad: Severidad
    valor_original: str
    valor_sugerido: str | None # solo en sugeridos (matching difuso)
    score: float | None         # solo en matching difuso

@dataclass(frozen=True)
class Veredicto:
    fila: int
    estado: Estado
    hallazgos: tuple[Hallazgo, ...]
```

**Unidad de decisión: la fila. Unidad de diagnóstico: el campo.** El reporte se ordena por fila y explica por campo.

## 4. Contrato de reglas (v1)

| ID | Campo | Severidad | Regla |
|---|---|---|---|
| `PRODUCT_NON_EMPTY` | producto | CRITICAL | No vacío tras normalización |
| `PRICE_FORMAT` | precio | CRITICAL | Parseable como número según el locale del proveedor |
| `PRICE_POSITIVE` | precio | CRITICAL | Mayor que cero |
| `CATEGORY_NON_EMPTY` | categoria | CRITICAL | No vacía tras normalización |
| `CATEGORY_IN_CATALOG` | categoria | CRITICAL / CORRECTIBLE | Escalera de matching (§5) |
| `DUPLICATE_ROW` | fila | higiene | Fila exactamente duplicada → se descarta con conteo |
| `PRICE_CONFLICT` | fila | CRITICAL | Mismo producto normalizado con precios distintos |

Las reglas son **datos, no código disperso**: registros declarativos (`Rule(id, field, severity, check, message)`) que el YAML por proveedor activa y parametriza. El segundo proveedor es configuración, no un segundo script.

## 5. Escalera de matching de categorías

Se aplica el valor normalizado del proveedor contra el catálogo normalizado de la PYME:

1. **Normalización determinista** (NFKC, casefold, sin acentos, sin puntuación) — resuelve la mayor parte de la "escritura como cada quien quiso" con riesgo cero.
2. **Match exacto** contra el catálogo → `aprobado` (higiene trazada si el valor cambió).
3. **Match por alias** definidos en el catálogo → `aprobado` (trazado).
4. **Fuzzy** (`rapidfuzz`) solo si 1–3 fallan: `WRatio ≥ 90` **y** margen ≥ 10 puntos sobre el segundo candidato → `sugerido` con `valor_sugerido` y `score`. No se aplica.
5. **Ambiguo** (top-2 demasiado cerca entre sí) → `sugerido` sin corrección; se reportan ambos candidatos.
6. **Sin match** → `rechazado` con motivo "categoría no existe en el catálogo de la PYME" (BN-3: integrar una categoría nueva es un flujo humano en el sistema de la PYME).

## 6. Pipeline

```
leer (defensivo) → normalizar (higiene trazada) → parsear precios (Decimal, locale)
    → validar (reglas como datos) → clasificar (aprobado / sugerido / rechazado + descartes)
    → generar (hoja limpia + hoja de devolución + CSV/JSON)
```

- Los duplicados exactos se descartan **antes** de validar, con conteo en el reporte.
- El conflicto "mismo producto, precios distintos" es CRITICAL: no se resuelve solo.

Interfaz v1 (CLI):

```
python -m dataguard validar <archivo-proveedor> --proveedor config/proveedores/<nombre>.yaml
```

Genera junto al archivo de entrada: `validos.xlsx`, `devolucion.xlsx` y `resultado.json` (prefijados por el nombre del archivo procesado).

## 7. Estructura de repositorio

```
dataguard/
├── src/
│   └── dataguard/
│       ├── __init__.py
│       ├── reading.py        # lectura defensiva del xlsx (strings, header_row, data_only)
│       ├── normalization.py  # normalización determinista + registro de higiene (idempotente)
│       ├── parsing.py        # precio → Decimal (locale por proveedor, cuantización 0.01)
│       ├── catalog.py        # carga y normalización del catálogo de la PYME
│       ├── matching.py       # escalera de matching (exacto → alias → fuzzy)
│       ├── rules.py          # registro declarativo de reglas
│       ├── engine.py         # pipeline por fila y clasificación
│       ├── report.py         # salidas: hoja limpia, hoja de devolución, CSV/JSON
│       └── cli.py            # interfaz de línea de comandos
├── config/
│   └── proveedores/
│       └── ejemplo.yaml      # mapeo de columnas, locale, header_row, catálogo, reglas activas
├── tests/
│   ├── fixtures/             # sucio.xlsx, catalogo.xlsx, salidas doradas
│   ├── test_normalization.py # hypothesis: normalize(normalize(x)) == normalize(x)
│   ├── test_rules.py         # reglas como funciones puras
│   ├── test_matching.py      # escalera de matching (incluye caso ambiguo)
│   └── test_engine.py        # golden files end-to-end
└── pyproject.toml
```

## 8. Salidas

1. **Hoja limpia** (filas `aprobado`): valores normalizados, precio cuantizado — lista para importar al sistema de la PYME.
2. **Hoja de devolución** (filas `sugerido` y `rechazado`): `fila`, `campo`, `valor_original`, `valor_sugerido`, `motivo`, `regla_id`, `score`. Dos audiencias: la PYME decide qué importar; el proveedor corrige su archivo.
3. **CSV/JSON estable** como contrato de integración — el Excel es interfaz para humanos; el CSV es el contrato para sistemas.

## 9. Estrategia de tests

- **Reglas como funciones puras** → testeables sin tocar Excel.
- **Golden files**: `fixtures/sucio.xlsx` + `fixtures/catalogo.xlsx` → salida esperada versionada.
- **Property-based testing** (`hypothesis`) para normalización: idempotencia `normalize(normalize(x)) == normalize(x)`.
- **Corpus de archivos sucios** que crece con cada proveedor nuevo.

## 10. Fuera de alcance v1

- Duplicados semánticos (mismo producto con distinto nombre).
- Matching difuso de nombres de producto.
- Base de datos y cualquier UI.
- Gestión del catálogo dentro de DataGuard (el catálogo vive en el sistema de la PYME; DataGuard solo lo lee).

La v1 es chica y honesta; eso es parte del diseño.
