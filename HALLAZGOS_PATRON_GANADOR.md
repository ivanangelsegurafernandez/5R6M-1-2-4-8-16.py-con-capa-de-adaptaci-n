# Hallazgos de patrón ganador (exploratorio)

Este análisis busca responder: **"¿hay algo repetible que aumente la tasa de éxito?"**

## 1) Línea base actual

- Dataset analizado: `dataset_incremental.csv`.
- Muestras: **257**.
- Tasa de acierto base (`result_bin=1`): **58.37%**.

## 2) Patrones más repetibles encontrados (reglas simples)

Se evaluaron reglas por pares de variables en extremos (`<=Q1` y `>=Q3`) y se midió el *lift* vs la línea base.

### Top señales (por lift)

1. **`rsi_9 >= Q3` + `rsi_reversion >= Q3`**  
   - WR: **80.00%** | Lift: **+21.63 pp** | n=40
2. **`rsi_9 >= Q3` + `es_rebote >= Q3`**  
   - WR: **79.49%** | Lift: **+21.12 pp** | n=39
3. **`rsi_9 >= Q3` + `puntaje_estrategia >= Q3`**  
   - WR: **77.78%** | Lift: **+19.41 pp** | n=36
4. **`rsi_14 >= Q3` + `rsi_reversion >= Q3`**  
   - WR: **73.33%** | Lift: **+14.97 pp** | n=30

## 3) Hipótesis operativa útil

Un patrón que se repite es:

- **Momentum + reversión “fuerte”** (RSI alto + señal de reversión alta) tiene mejor desempeño que el promedio.
- En lenguaje práctico: cuando hay una condición de sobreextensión confirmada por la capa de reversión, el sistema acierta más.

## 4) Cómo explotarlo sin sobreajustar

Propuesta de regla de priorización (no hard lock al inicio):

- **Prioridad Alta**: si `rsi_9>=Q3` y además (`rsi_reversion>=Q3` o `es_rebote>=Q3`).
- **Prioridad Media**: si solo una de las condiciones está en Q3.
- **No operar / esperar**: cuando no hay confirmación dual y la probabilidad IA está cerca del umbral.

## 5) Ideas concretas para subir tasa de éxito

1. **Filtro de doble confirmación** antes de entrar (RSI extremo + reversión/rebote).
2. **Ranking por lift histórico** por bot en vez de usar solo probabilidad IA instantánea.
3. **Umbral dinámico por régimen**: más estricto cuando sube volatilidad y más laxo en régimen estable.
4. **Control de racha de pérdidas**: si el bot cae en drawdown corto, exigir confirmación dual para volver a entrar.
5. **Reentreno por ventana móvil** para evitar que una regla vieja se vuelva ruido.

## 6) Advertencia importante

- Estos hallazgos son **exploratorios** y pueden cambiar con más datos.
- Deben validarse en *walk-forward* y luego en real con stake pequeño.

---

## Script reproducible

Se agregó `analisis_patron_ganador.py` para recalcular este resumen automáticamente con el dataset actual.
