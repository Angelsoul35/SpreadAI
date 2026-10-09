# 4. Validación con datos reales

Los capítulos anteriores usan estados **generados** por el proyecto. Este capítulo valida
SpreadAI sobre **estados financieros reales** y demuestra que el resultado generaliza (ni
sobreajuste / *overfitting*, ni subajuste / *underfitting*). Todo el código vive en
`spreadai/real_data.py` y `spreadai/real_benchmark.py`; se corre con `make benchmark`.

## La tarea

El dataset **American Bankruptcy** (Lombardo et al., *Future Internet* 2022) es un panel de
empresas públicas de EE. UU. tomado de Compustat, 1999–2018. Cada registro trae **tres años
fiscales** de partidas contables por empresa y una etiqueta **a futuro**: `failed` si la
empresa se declaró en quiebra (Chapter 7/11) el año siguiente, `alive` en caso contrario.

La pregunta que respondemos es la que un analista de crédito realmente hace:
**¿esta empresa quiebra el próximo año?** Y la respondemos **reusando el pipeline de
SpreadAI de punta a punta**:

```
partidas reales → texto etiquetado → parse_text (extractor real)
               → validate (identidad contable + confianza) → compute_ratios
               → 9 ratios × 3 años + tendencias → clasificador (regresión logística)
```

Es decir, las variables que entran al modelo **son la salida de SpreadAI**, no otras.

## Dataset y mapeo de campos / etiqueta

| Split | Filas | Año de predicción | `failed` |
|---|---|---|---|
| `financial_train.csv` | 3.142 | 2001–2014 | 403 |
| `financial_validation.csv` | 233 | 2015 | 27 |
| `financial_test.csv` (held-out) | 2.815 | 2016–2018 | 72 |

Cada año trae 18 partidas. SpreadAI espera su esquema canónico, así que `real_data.py`
las mapea (detalle completo en [`datasets/README.md`](../../datasets/README.md)). Lo clave:

* El **patrimonio es la partida que cuadra**: `common_equity = (activos − pasivos) −
  utilidades retenidas`. Así se cumple `activos = pasivos + patrimonio` y la extracción
  valida — igual que en un balance real, donde el capital es el residuo que cuadra la hoja.
* La fuente **no reporta intereses**, así que `interest_coverage` queda indefinido y se
  descarta del vector de variables.
* La fuente no separa caja / proveedores / deuda de corto plazo; esas líneas quedan en 0 o
  en residuos, por eso la **cobertura de extracción es 13/18 ≈ 0,722**. Los ratios que
  SpreadAI calcula no dependen de las líneas ausentes.

## Las métricas, con fórmulas

Como solo el **2,6 %** del held-out es `failed`, la *accuracy* simple engaña (decir siempre
"alive" acierta el 97,4 %). Por eso usamos métricas robustas al desbalance:

* **ROC-AUC** = probabilidad de que el modelo le dé mayor puntaje a una empresa que quebró
  que a una que no. Con `n₊` positivos y `n₋` negativos:

  $$\text{AUC} = \frac{1}{n_+ n_-} \sum_{i \in +} \sum_{j \in -} \big[\, s_i > s_j \,\big]
  \quad(\text{empates cuentan } 0{,}5)$$

  Un modelo sin información da **0,5**; uno perfecto, 1,0.

* **Average Precision (AP)** = área bajo la curva precisión–recall,
  $\text{AP} = \sum_k (R_k - R_{k-1})\,P_k$, con
  $P = \tfrac{TP}{TP+FP}$ (precisión) y $R = \tfrac{TP}{TP+FN}$ (recall). El piso de un
  modelo sin información es la **prevalencia** (0,026 aquí).

* **Balanced accuracy** = promedio de sensibilidad y especificidad:

  $$\text{bal.acc} = \tfrac{1}{2}\left(\underbrace{\tfrac{TP}{TP+FN}}_{\text{sensibilidad}}
  + \underbrace{\tfrac{TN}{TN+FP}}_{\text{especificidad}}\right)$$

### Ejemplo numérico 1 — los ratios de una empresa real

Empresa `C2`, año fiscal 2010, etiqueta `failed`. Partidas reales (en millones):
activos corrientes 6.838, inventario 594, pasivos corrientes 8.780, activos totales 25.088,
pasivos totales 29.033, deuda de largo plazo 9.253, utilidades retenidas −8.362,
ingresos 22.170, costo de ventas 18.138, EBIT 308, utilidad neta −471.

SpreadAI calcula (y así entrena el modelo):

| Ratio | Fórmula | Cálculo | Valor |
|---|---|---|---|
| Current ratio | act. corr. / pas. corr. | 6.838 / 8.780 | **0,779** (< 1: iliquidez) |
| Quick ratio | (act. corr. − inv.) / pas. corr. | 6.244 / 8.780 | 0,711 |
| Patrimonio | activos − pasivos | 25.088 − 29.033 | **−3.945** (negativo) |
| Debt-to-assets | pasivos / activos | 29.033 / 25.088 | **1,157** (> 1: insolvente) |
| Net margin | utilidad neta / ingresos | −471 / 22.170 | **−0,021** (pérdida) |

Tres señales de alarma a la vez — iliquidez, patrimonio negativo y pérdida — que el modelo
aprende a asociar con la quiebra. Este es exactamente el tipo de estado que SpreadAI marca.

### Ejemplo numérico 2 — balanced accuracy en el held-out

Con umbral 0,5 sobre los 2.815 registros de prueba, la matriz de confusión real es:

|  | predice quiebra | predice vive |
|---|---|---|
| **quebró** (72) | TP = 54 | FN = 18 |
| **vivió** (2.743) | FP = 1.230 | TN = 1.513 |

$$\text{sensibilidad} = \tfrac{54}{72} = 0{,}750 \qquad
\text{especificidad} = \tfrac{1.513}{2.743} = 0{,}552$$
$$\text{bal.acc} = \tfrac{1}{2}(0{,}750 + 0{,}552) = \mathbf{0{,}651}$$

El modelo **detecta 54 de las 72 quiebras reales (75 %)** a cambio de mandar a revisión 1.230
empresas sanas. Es una postura conservadora, coherente con la filosofía de SpreadAI: ante la
duda, a revisión humana.

## CV vs. held-out, y la brecha train/test

| Medición | ROC-AUC |
|---|---|
| Baseline (mayoría) | 0,500 |
| Validación cruzada estratificada 5-fold (train) | **0,707 ± 0,022** |
| Train (ajuste en todo el train) | 0,739 |
| **Held-out (2016–2018, nunca visto)** | **0,712** |

Dos lecturas:

* **Brecha train − held-out = +0,027.** Estrecha. El modelo es una regresión logística
  regularizada: *no puede* memorizar, así que una brecha grande sería una alarma real, no un
  artefacto de capacidad.
* **CV ↔ held-out = 0,707 vs. 0,712 (brecha −0,005).** Lo que mide la validación cruzada
  dentro del train **coincide** con lo que ocurre en años futuros no vistos. Esa coincidencia
  — no la brecha con el train — es la prueba de generalización.

> **Sobreajuste vs. subajuste.** Sobreajuste = el modelo memoriza el train y falla fuera
> (CV o held-out muy por debajo del train). Subajuste = no aprende nada útil (held-out no
> supera el baseline). Aquí no ocurre ninguno: held-out (0,712) supera con holgura el
> baseline (0,500) y concuerda con la CV.

## El control negativo

Un buen resultado podría ser una fuga de datos (*leakage*). Para descartarlo corremos dos
controles que **deben** colapsar al azar (AUC ≈ 0,5):

1. **Etiquetas barajadas:** se permuta `y` en el train. CV AUC → **0,491**.
2. **Variables revueltas:** se permuta cada columna de forma independiente, destruyendo la
   estructura por fila. Held-out AUC → **0,533**.

Ambos caen a ~0,5. Si el pipeline "acertara" con etiquetas aleatorias, habría fuga; no la hay.

## Derivación del veredicto

`classify_fit` en `real_benchmark.py` decide con reglas explícitas, en orden:

1. Si algún control negativo se aleja del azar (> 0,07) → `invalid` (hay fuga).
2. Si el held-out no supera el baseline por al menos 0,05 → `underfit`.
3. Si CV y held-out difieren en más de 0,10 → `overfit`.
4. Si no → `well-fit`.

Con los números reales: controles en ~0,5 (pasa 1); held-out 0,712 > 0,500 + 0,05 (pasa 2);
|0,707 − 0,712| = 0,005 ≤ 0,10 (pasa 3) ⟹ **`well-fit`**.

La prueba `test_verdict_discriminates_real_from_shuffled` confirma que el veredicto
discrimina: con etiquetas reales da `well-fit`; con etiquetas barajadas **no**.

> **La idea central.** No afirmamos un número bonito: lo **derivamos** de baseline, CV,
> held-out y controles negativos, y lo dejamos que una prueba automática lo rete. Un AUC de
> 1,0 sería sospechoso; 0,71 que generaliza a años futuros es un resultado real y defendible.
