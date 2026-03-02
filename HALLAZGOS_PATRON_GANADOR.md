# Hallazgos: patrón prometedor con drift

Este análisis ya **no** se presenta como “patrón ganador definitivo”.
Se presenta como **patrón prometedor** que debe vigilarse por **drift**.

## Qué hace ahora `analisis_patron_ganador.py`

```bash
python analisis_patron_ganador.py
```

Genera un reporte en consola con 4 bloques:

1. **Top reglas duales** por lift (`<=Q1` / `>=Q3`).
2. **Pattern Score + veto tardío** (penaliza persecución de racha sin confirmación dual).
3. **Persistencia por 3 ventanas cronológicas** para medir drift.
4. **Ranking híbrido v1 (proxy)** para llevar el hallazgo a lógica operativa.

## Idea operativa implementada

- **Pattern Score** (suma):
  - `rsi_9>=Q3` (+2)
  - `rsi_reversion>=Q3` (+2)
  - `es_rebote>=Q3` (+2)
  - `puntaje_estrategia>=Q3` (+1)
  - `cruce_sma>=Q3` (+1)
  - `breakout>=Q3` (+1)
  - `payout>=Q3` (+1)
  - `volatilidad<=Q2` (+1)
- **Bonus dual** (+1): si hay confirmación dual de reversión/rebote con `rsi_9` alto.
- **Veto tardío / penalización** (-2): si `racha_actual` está alta pero sin confirmación dual.

## Comandos útiles

```bash
# reporte estándar
python analisis_patron_ganador.py

# ajustar sensibilidad
python analisis_patron_ganador.py --score-th 6 --min-muestras 25 --top 15

# guardar reporte
python analisis_patron_ganador.py --guardar reporte_patrones.txt
```

## Interpretación correcta

- Si el patrón gana en una ventana y cae en otra, hay drift.
- Úsalo como filtro/ranking de contexto, no como hard-rule única.
- Paso siguiente: integrar este score con `prob_ia_oper`, `confirm=2/2`, `trigger_ok` y bloqueos reales del runtime.
