# Hallazgos de patrón ganador (exploratorio)

Este análisis responde: **"¿hay algo repetible que aumente la tasa de éxito?"**

## ¿Qué hace `analisis_patron_ganador.py`?

1. Carga `dataset_incremental.csv` (o el CSV que indiques con `--dataset`).
2. Calcula la tasa base de acierto (`result_bin=1`).
3. Busca reglas de 2 variables en extremos (`<=Q1` y `>=Q3`).
4. Ordena por **lift** (cuánto mejora sobre la tasa base).
5. Imprime reporte en consola y opcionalmente lo guarda con `--guardar`.

## Cómo correrlo (rápido)

```bash
python analisis_patron_ganador.py
```

Si quieres más reglas o menos restricción de tamaño mínimo:

```bash
python analisis_patron_ganador.py --top 15 --min-muestras 20
```

Si quieres guardar resultados a archivo:

```bash
python analisis_patron_ganador.py --guardar reporte_patrones.txt
```

## Línea base actual (con el dataset del repo)

- Muestras: **257**
- Win rate base: **58.37%**

## Patrones más fuertes encontrados

1. `rsi_9 >= Q3` + `rsi_reversion >= Q3` → WR **80.00%** (lift **+21.63 pp**, n=40)
2. `rsi_9 >= Q3` + `es_rebote >= Q3` → WR **79.49%** (lift **+21.12 pp**, n=39)
3. `rsi_9 >= Q3` + `puntaje_estrategia >= Q3` → WR **77.78%** (lift **+19.41 pp**, n=36)
4. `rsi_14 >= Q3` + `rsi_reversion >= Q3` → WR **73.33%** (lift **+14.97 pp**, n=30)

## Interpretación operativa

Patrón repetido: **momentum alto + confirmación de reversión/rebote**.

Traducción práctica:

- **Prioridad alta**: `rsi_9` en Q3 y además `rsi_reversion` o `es_rebote` en Q3.
- **Prioridad media**: solo una confirmación.
- **Esperar/no operar**: sin confirmación dual y probabilidad IA cerca del umbral.

## Advertencia

Estos hallazgos son exploratorios y deben validarse en *walk-forward* y luego con stake pequeño en real.
