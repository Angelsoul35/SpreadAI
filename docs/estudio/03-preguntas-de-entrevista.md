# 3. Preguntas de entrevista

## Nivel junior / media

**¿Qué hace SpreadAI en una frase?**
Lee un estado financiero (texto o PDF), lo lleva a un formato estándar, verifica que cuadre,
calcula ratios de crédito y redacta un memo, mandando a revisión humana lo que no sea
confiable.

**¿Qué es "spread" un estado financiero?**
Copiar cada línea del estado a una plantilla estándar, verificar que sume y calcular ratios.
Es el primer paso del análisis de crédito. SpreadAI lo automatiza.

**¿Cómo manejas etiquetas distintas como "Sales" o "Ventas"?**
Con un mapa de etiquetas y alias (`labels.py`): varias etiquetas posibles apuntan a la misma
clave estándar. El parser las reconoce sin importar cómo se llamen.

## Nivel media / senior

**¿Cuál es tu verificación principal y por qué?**
La identidad contable: activos = pasivos + patrimonio. Es una señal barata y fuerte de que la
extracción está bien. Si no cuadra, bajo la confianza y mando a revisión.

**¿Cómo decides cuándo un caso va a revisión humana?**
Con un puntaje de confianza (cobertura de campos ajustada por las verificaciones). Si está
por debajo del umbral o el estado no cuadra, se marca para revisión. La herramienta no
esconde una extracción dudosa.

**¿Qué pasa con los PDF escaneados?**
Un PDF normal se lee con pdfplumber. Uno escaneado es una imagen, así que necesita OCR
(opcional: `spreadai[ocr]` + tesseract). Si no hay OCR y el PDF no tiene texto, devuelvo un
error claro en vez de resultados vacíos.

**¿Por qué el LLM es agnóstico de proveedor?**
Para no depender de un solo vendedor: los precios cambian, un proveedor puede caerse, y
algunos despliegues necesitan un modelo local por privacidad. Uso una interfaz común con una
cascada que cae al siguiente proveedor si uno falla.

## Nivel senior / diseño

**¿Cómo conecta esto con un sistema de decisión de crédito?**
El "spread" y los ratios alimentan al modelo de riesgo (por ejemplo, CreditTrace). SpreadAI
es la capa de entrada: convierte documentos en datos verificados y confiables.

**¿Qué le falta para producción?**
Soporte para más formatos (tablas complejas, multi-página, multi-idioma), un modelo de
confianza aprendido en vez de heurístico, trazabilidad de cada número a su lugar en el
documento, y pruebas con estados reales anonimizados.

## Reto para ti

* Agrega trazabilidad: guarda, para cada número, la línea del documento de donde salió.
* Cambia el puntaje de confianza heurístico por uno calibrado contra revisiones humanas.
* Agrega un segundo período y calcula variaciones año contra año (crecimiento de ingresos,
  cambio en apalancamiento).
