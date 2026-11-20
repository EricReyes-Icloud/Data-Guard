# DataGuard — Propuesta técnica y opinión senior

> Documento de diseño técnico derivado de `summary.md`.
> Estado: propuesta cerrada — modelo de entrada confirmado (2026-11-11). El diseño técnico cerrado vive en `design.md`.

## Veredicto

La propuesta es sólida y, de las tres ideas del proyecto, es la que más valor real tiene.

Pero seamos claros: `summary.md` es un excelente *pitch*, todavía no es un diseño. Abajo se detalla dónde está firme, dónde se queda corto y qué decisiones técnicas haría un perfil senior en automatización, datos y Python.

---

## Dónde está bien

- **"Validar antes de procesar"** es la decisión correcta. La mayoría de los scripts del mercado convierten y listo; acá se ataca el problema en el punto donde se origina.
- **Las cuatro etapas** (normalizar → validar → clasificar → generar) son el esqueleto correcto.
- **No auto-corregir todo** es el instinto más senior de todo el documento. Esa decisión hay que sostenerla con firmeza.

---

## Los tres huecos que definen la arquitectura

### 1. No se especifican los dos archivos de entrada

Esto define el 60% del diseño.

La lectura del documento sugiere:

- **Archivo A — Catálogo maestro**: SKU, categoría, unidad de medida, referencia válida.
- **Archivo B — Lista de precios del proveedor**: los datos a validar.

Si el modelo es ese, el corazón del sistema **no es "limpiar un Excel"**, es **integridad referencial entre dos fuentes**. El cruce es donde vive el valor y donde vive la complejidad.

Si en cambio son dos archivos del mismo proveedor que se contradicen entre sí (por ejemplo, lista de productos + lista de precios), el problema es otro: **reconciliación con conflictos**. El diseño cambia.

> **Resuelto (2026-11-11):** ninguno de los dos modelos. El proveedor entrega **un solo archivo** (`productos`, `categoria`, `precio`) y el catálogo de categorías vive del lado de la PYME, que es la fuente de verdad. Ver `design.md` para el diseño cerrado.

### 2. Se mezcla la granularidad de fila con la de campo

El documento habla de "fila aprobada / fila rechazada", pero los hallazgos son por campo (`precio`, `categoría`, `SKU`, `unidad`).

La distinción necesaria:

- **Unidad de decisión:** la fila.
- **Unidad de diagnóstico:** el campo.

Sin separar ambas, el reporte de errores deja de ser útil para quien tiene que corregir el archivo.

### 3. "Corregir pequeños errores de tipeo" sin criterio es peligroso

Una búsqueda de similitud con parámetros por defecto puede "corregir" *Cemento* → *Cemento Blanco* sin que nadie lo note.

Esto necesita un criterio explícito y conservador (ver *Matching difuso*).

---

## Propuesta de diseño

### Reglas como datos, no como código

Si las reglas son condicionales dispersos, el segundo proveedor obliga a escribir un segundo script. En cambio, un registro declarativo:

```python
Rule(
    id="PRICE_POSITIVE",
    field="precio",
    severity=Severity.CRITICAL,
    check=lambda v: v > 0,
    message="El precio debe ser mayor a cero",
)
```

Cada proveedor aporta un YAML con:

- qué reglas aplican,
- qué columna del Excel mapea a qué campo del dominio,
- qué catálogo de referencia usa.

Ahí está la reutilización que menciona el pitch, pero **diseñada desde el día uno**, no parcheada después.

### Tres estados de fila + un registro aparte

El modelo de tres resultados es correcto, pero conviene afinarlo:

| Estado | Qué pasó | Qué hace el sistema |
|---|---|---|
| `aprobado` | cumple todas las reglas | pasa a la hoja limpia |
| `sugerido` | hay una corrección probable pero no cierta | **no** se aplica; va a rechazados con `valor_sugerido` y score |
| `rechazado` | viola una regla dura | bloquea la fila |

Aparte, un registro `normalizations_applied` por fila: trim, casefold, acentos, unificación de `"N/A"`, `"-"` y vacíos.

Eso **no es un error**, es higiene: se aplica y se deja trazado. Mezclar higiene con corrección sugerida diluye el concepto y obliga a revisar manualmente cosas que no lo necesitan.

### Matching difuso: umbral y margen, nunca automático

Escalera de resolución:

1. **Normalización determinista** (NFKC, casefold, sin acentos, sin puntuación) → resuelve la mayor parte de los "typos" con riesgo cero.
2. **Match exacto** contra catálogo + aliases (`"Condimentos"`, `"CONDIMENTO"`, `"Condim."`).
3. **Fuzzy** recién ahí, con `rapidfuzz` y dos condiciones simultáneas:
   - `WRatio ≥ 90`
   - margen ≥ 10 puntos sobre el segundo candidato.
4. Si el top-2 está cerca, el caso es **ambiguo** → `sugerido`, no se adivina.
5. El score siempre va al reporte. La decisión final es humana.

---

## Decisiones técnicas no opinables

- **`Decimal`, nunca `float`, para dinero.** `float` produce artefactos como `1234.5599999` y después el precio importado no coincide con el del proveedor. Usar `quantize(Decimal("0.01"), ROUND_HALF_UP)`.
- **Leer todo como string y parsear explícitamente.** `pd.read_excel(..., dtype=str, keep_default_na=False, na_values=[])`. Así se distingue vacío real de `NaN` y no se pierden SKUs con ceros a la izquierda (si Excel ya los eliminó, no hay recuperación posible: hay que marcarlo como sospechoso).
- **`header_row` configurable.** La mayoría de los Excel de proveedores traen dos o tres filas de título antes del encabezado real. Sin esto, el sistema es un juguete.
- **`data_only=True` es una trampa.** Si el archivo tiene fórmulas y nunca se abrió en Excel, `openpyxl` devuelve `None`. Hay que detectarlo y avisar con un mensaje claro, no fallar de forma opaca.
- **Locale explícito.** `"1.234,56"` vs `"1,234.56"` no se adivina: se configura por proveedor.
- **El archivo de entrada es inmutable.** Nunca se escribe sobre el original.
- **Excel es formato de entrega, no de integración.** Generar además CSV/JSON estable. El día que esto se conecte a un sistema, el contrato es el CSV; el Excel es la interfaz para humanos.

---

## Fuera de alcance en la v1

- Duplicados semánticos (mismo producto con distinto SKU).
- Matching difuso de nombres de producto.
- Base de datos.
- Cualquier tipo de UI.

La gracia del proyecto es que es chico y honesto. Sumar eso lo convierte en un ERP a medio hacer.

### Nota sobre duplicados

No es **una** regla, son **tres** problemas distintos:

1. **Fila exactamente duplicada** → se descarta, con conteo.
2. **Mismo SKU con precios distintos** → conflicto, severidad **crítica**, no se resuelve solo.
3. **Mismo producto con distinto SKU** → fuera de alcance en v1.

Conviene nombrarlos por separado en la documentación del proyecto.

---

## El diferencial real: los tests

Esto es lo que separa un script de un sistema, y lo que demuestra criterio de ingeniería:

- **Reglas como funciones puras** → testeables sin tocar Excel.
- **Golden files**: `fixtures/sucio.xlsx` + `catalogo.xlsx` → salida esperada. Es la prueba de que funciona de verdad.
- **Property-based testing** (`hypothesis`) para normalización: `normalize(normalize(x)) == normalize(x)`. La idempotencia es una propiedad, no un caso de prueba.
- **Corpus de archivos sucios reales** que crece con cada proveedor nuevo.

---

## Idea de producto: el reporte tiene dos audiencias

El archivo de rechazados sirve a dos destinatarios distintos:

- **La PYME**, que decide qué importar.
- **El proveedor**, que tiene que corregir su archivo.

Diseñar esa hoja como un documento de *devolución al proveedor* — con `fila`, `campo`, `valor_original`, `motivo` y `regla_id` — convierte el output en una herramienta de gestión, no en un log técnico.

---

## Pregunta cerrada (2026-11-11)

**Respuesta confirmada:** el proveedor entrega **un solo archivo Excel** — una lista de precios con tres columnas (`productos`, `categoria`, `precio`) — y la PYME carga esos precios a su sistema.

Sobre el catálogo de categorías: **la fuente de verdad es el catálogo que la PYME ya tiene**. Ejemplo: el proveedor envía "adesivos" y el catálogo oficial de la PYME tiene "adhesivos" → gana "adhesivos", porque son los sistemas de la PYME los que importan la información nueva del proveedor, que debe coincidir con su catálogo actual — salvo que se integre un producto nuevo (flujo humano, fuera de DataGuard).

Con ambas decisiones el diseño técnico queda cerrado en `design.md`: modelo de dominio, contrato de reglas y estructura de repositorio.
