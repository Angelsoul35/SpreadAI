# Guía de estudio — SpreadAI

Esta guía está en español y explica el proyecto para que lo estudies y lo sustentes en una
entrevista. El código y la documentación técnica están en inglés; aquí va el *por qué*.

## Orden de lectura

1. [Extracción y Document AI](01-extraccion.md) — cómo se leen los estados financieros
   (texto, PDF, OCR, LLM) y cómo se llevan a un esquema estándar.
2. [Validación, confianza y ratios](02-validacion-y-ratios.md) — la identidad contable, el
   puntaje de confianza, la revisión humana y los ratios de crédito.
3. [Preguntas de entrevista](03-preguntas-de-entrevista.md) — preguntas típicas con
   respuestas.
4. [Validación con datos reales](04-validacion-datos-reales.md) — correr el pipeline sobre
   estados financieros reales (American Bankruptcy), con baseline, validación cruzada,
   held-out, control negativo y el veredicto de generalización (ni sobreajuste ni subajuste).

## Cómo correrlo mientras estudias

```bash
make install
make demo       # genera un estado, lo "spread", imprime ratios y memo
make test       # 34 pruebas
make benchmark  # valida el pipeline sobre el panel real de empresas
```

El concepto central: **"spread" (vaciar) un estado financiero a un formato estándar,
verificar que cuadre, calcular ratios y redactar un memo — mandando a revisión humana lo
que no sea confiable.**
