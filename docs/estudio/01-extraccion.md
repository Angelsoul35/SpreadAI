# 1. Extracción y Document AI

## El problema

Un estado financiero llega como texto o como PDF, con formatos distintos y etiquetas que
varían ("Ventas", "Sales", "Ingresos"). "Spread" significa llevar todos esos números a un
**esquema estándar** (el mismo para todas las empresas), para poder compararlos y
verificarlos igual.

## Esquema estándar

En `spreadai/schema.py` definimos el formato fijo: un **balance** (activos, pasivos,
patrimonio) y un **estado de resultados** (ingresos, costos, gastos, intereses,
impuestos), con totales calculados como propiedades. Ese es el destino de toda extracción.

## Tres caminos de extracción

Todos devuelven un `ExtractionResult` con el estado y la **cobertura de campos** (cuántas
de las líneas estándar se encontraron).

### 1. Parser de texto (determinista)

En `extract/text_parser.py`. Lee líneas tipo `Etiqueta: monto`, mapea la etiqueta a una
clave estándar usando `labels.py` (etiqueta principal o un **alias** como "COGS" →
`cost_of_goods_sold`), y parsea el monto. El parseo de montos maneja separadores de miles,
paréntesis para negativos y signos de moneda. Es rápido, gratis y repetible.

### 2. Lector de PDF

En `extract/pdf.py`. Con **pdfplumber** saca el texto de un PDF normal. Si el PDF está
**escaneado** (es una imagen), no hay texto, así que necesita **OCR**.

> **Concepto — OCR (Optical Character Recognition).** Convierte una imagen de texto en
> texto editable. Aquí es opcional: requiere el extra `spreadai[ocr]` y el binario
> `tesseract`. Si no está disponible y el PDF no tiene texto, devolvemos un error claro en
> vez de resultados vacíos.

### 3. Extractor con LLM (fallback)

En `extract/llm_extractor.py`. Para estados "sucios" (prosa, formatos raros), le pedimos a
un LLM que devuelva las claves estándar en JSON. Usa la **cascada de proveedores**
(agnóstica), así que no depende de un solo vendedor. En las pruebas se inyecta un cliente
falso, así que nada llega a una API real.

## Document AI, en resumen

Document AI es justamente esto: convertir documentos no estructurados (PDF, imágenes) en
datos estructurados y verificables. La clave de este proyecto es que no se queda en
"extraer": **verifica** lo extraído (capítulo 2) antes de confiar en ello.
