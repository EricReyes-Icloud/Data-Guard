## Validador de datos con reglas de negocio (Excel de proveedores)

### Resumen

- El problema: Los proveedores envían listas de precios en archivos Excel llenos de errores (filas duplicadas, precios en cero, categorías mal escritas). Si se cargan directo al sistema, el error se queda viviendo ahí y cuesta dinero.

- La solución: En lugar de solo convertir el archivo, el script valida los datos: verifica precios mayores a cero, corrige pequeños errores de tipeo en categorías contra un catálogo y separa los errores.

- Resultado para el usuario: Entrega una hoja limpia para importar al sistema y otra hoja de errores marcados en rojo con su motivo (duplicados, precios imposibles, etc.).

- Habilidad demostrada: Aplicar reglas de negocio para validar datos antes de procesarlos o cargarlos a un sistema.

### Opinion Personal

Esta es, personalmente, mi favorita de las tres.

Y no necesariamente porque sea la más compleja, sino porque representa una necesidad que aparece en prácticamente cualquier empresa que maneje información proveniente de terceros.

El problema no es recibir información. El problema es confiar en ella sin verificarla.

Imagina que una empresa recibe un Excel con 500 productos de un proveedor.

El archivo contiene:

- Productos duplicados.
- Precios en cero.
- Categorías escritas incorrectamente.
- Nombres inconsistentes.
- Referencias inexistentes.
- Unidades de medida equivocadas.

Si la empresa importa directamente ese archivo a su inventario, los errores pueden terminar afectando las compras, los precios, las existencias y las ventas.

### Mi análisis técnico

La propuesta tiene un enfoque muy interesante: validar antes de procesar.

Yo dividiría el programa en cuatro etapas:

#### 1. Normalización

Estandarizar la información antes de validarla.

Por ejemplo:
- Eliminar espacios innecesarios.
- Homogeneizar mayúsculas y minúsculas.
- Normalizar formatos numéricos.
- Estandarizar nombres de categorías.

#### 2. Validación

Aplicar reglas de negocio:

Campo	Regla

Nombre	No puede estar vacío
Precio	Debe ser mayor que cero
SKU	Debe ser único
Categoría	Debe existir en el catálogo
Unidad	Debe pertenecer a las permitidas
Referencia	Debe cumplir el formato establecido

#### 3. Clasificación de errores

No todos los errores deberían tratarse de la misma manera.

Por ejemplo:

- Error crítico: precio en cero.
- Error de integridad: SKU duplicado.
- Error corregible: categoría con un error tipográfico.
- Advertencia: nombre con formato inconsistente.

#### 4. Generación de resultados

El programa entrega dos archivos:

**Datos válidos**

Información lista para revisión e importación.

**Datos rechazados**

Errores identificados y explicación de cada uno.

### Una mejora que considero especialmente importante

No corregiría automáticamente todos los errores.

Por ejemplo, supongamos que el proveedor envía:

- Categoría: Condimetos.
- Catálogo: Condimentos.

El programa puede identificar que probablemente se trata de un error tipográfico.

Pero debería conservar el valor original y registrar la corrección sugerida.

¿Por qué?

Porque una corrección automática equivocada puede ser más peligrosa que el error original.

Implementaría un sistema de validación con tres resultados:

- Aprobado: cumple todas las reglas.
- Corregible: existe una sugerencia de normalización.
- Rechazado: requiere intervención humana.

Esto es particularmente interesante porque combina automatización con supervisión humana.

### Mi veredicto:

Es el proyecto que mejor demuestra pensamiento de ingeniería de software, manejo de datos, reglas de negocio y prevención de errores.

Además, tiene un potencial de reutilización enorme: puedes adaptar el motor de validación a proveedores, inventarios, clientes, facturación y otros procesos.