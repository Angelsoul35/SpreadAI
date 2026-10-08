# 2. Validación, confianza y ratios

## La identidad contable

La verificación principal es la **ecuación contable fundamental**:

```
Activos = Pasivos + Patrimonio
```

Si se cumple (dentro de una tolerancia pequeña), lo más probable es que la extracción esté
bien. Si no cuadra, algo salió mal: una línea faltante, un dígito mal leído, una etiqueta
mapeada a la clave equivocada. Es una señal barata y fuerte. (Ver
[ADR-0002](../adr/0002-validate-the-accounting-identity.md).)

## El puntaje de confianza

En `validate.py`, la confianza parte de la **cobertura de campos** y baja cuando:

* el estado no cuadra (× 0.4),
* no hay ingresos (× 0.6),
* hay montos negativos en partidas que no deberían serlo (× 0.7).

## Revisión humana

Si la confianza está por debajo del umbral (configurable con
`SA_CONFIDENCE_REVIEW_THRESHOLD`) **o** el estado no cuadra, el resultado se marca
`needs_human_review`. Esta es la regla de seguridad: la herramienta hace el primer pase,
pero no esconde una extracción dudosa. (Ver
[ADR-0003](../adr/0003-confidence-and-human-review.md).)

> **Por qué importa.** Un "spread" mal hecho que se use en una decisión de crédito cuesta
> dinero real. Una herramienta que siempre responde, aunque esté equivocada, es peligrosa.
> Saber cuándo **no** confiar es tan importante como extraer bien.

## Los ratios de crédito

En `ratios.py`. Cada ratio devuelve `None` si el denominador es cero, para no romperse con
datos incompletos.

| Grupo | Ratio | Qué dice |
|---|---|---|
| Liquidez | Current ratio | ¿Los activos corrientes cubren los pasivos corrientes? (>1 mejor) |
| Liquidez | Quick ratio | Igual, pero sin inventario (más estricto) |
| Apalancamiento | Debt-to-equity | Deuda frente a patrimonio (más alto = más riesgo) |
| Apalancamiento | Interest coverage | Utilidad operativa / intereses (más alto = más seguro) |
| Rentabilidad | Net margin | Utilidad neta / ingresos |
| Rentabilidad | ROA / ROE | Retorno sobre activos / sobre patrimonio |

## El memo de crédito

En `memo.py`. Dos modos: `template` (determinista, arma el memo con los números, sin LLM) y
`llm` (lo redacta la cascada de proveedores). El memo incluye los totales, los ratios clave
y una nota de calidad de datos (si cuadra y la confianza), y avisa si debe ir a revisión.
