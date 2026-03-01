# Análisis y plan de mejora para `5R6M-1-2-4-8-16.py`

## Diagnóstico rápido

1. El sistema ya tiene bastantes defensas anti-sobreconfianza (shrinkage, cap en warmup, umbrales y auditoría), pero su efectividad actual está limitada por **muy poca muestra cerrada** para validar calibración real.
2. El último reporte indica sobreconfianza fuerte en el rango 90–100% (prob media 97.3% vs winrate real 54.5%), lo que sugiere que la `Prob IA` todavía no representa bien la probabilidad real observada.
3. La base técnica para calibrar mejor ya existe en el código (calibrador sigmoid/isotonic + auditorías + umbral adaptativo), por lo que la mejora más rentable es **operativa y de gobernanza de datos**, no “cambiar todo el modelo”.

## Evidencia encontrada

- Umbrales y controles anti-sobreconfianza definidos en configuración global (`IA_SHRINK_ALPHA`, límites de warmup y caps).  
- Wrapper explícito de calibración de probabilidad (`ModeloXGBCalibrado`) con opciones `sigmoid` e `isotonic`.  
- Umbral REAL adaptativo implementado, pero anulado por `REAL_CLASSIC_GATE=True` (fuerza 85% fijo).  
- Reporte integral con n muy bajo de señales cerradas y brecha alta en bucket 90–100%.

## ¿Necesitamos que la Prob IA sea más real y acertada?

Sí. Hoy la prioridad no es subir “porcentaje mostrado”, sino alinear:

- **Prob predicha** (lo que muestra HUD),
- **Winrate observado** (lo que realmente pasa),
- **Decisión operativa REAL** (cuándo dejar pasar señales).

Esa alineación se logra con calibración + suficiente muestra + reglas de activación por confianza estadística.

## Plan recomendado (en orden)

### Fase 1 (inmediata, bajo riesgo)

1. Mantener operación en **shadow mode** hasta llegar al mínimo de muestra útil (>=80 cierres, ideal >=200 para estabilidad).
2. Activar checkpoint automático cada +20 cierres para recalcular:
   - ECE/Brier,
   - precisión por buckets (70–80, 80–90, 90–100),
   - gap `Prob IA - Winrate` por bot.
3. Forzar una regla de seguridad temporal: si bucket 90–100% tiene gap > 15pp y n>=20, aplicar cap adicional dinámico (ej. `p_final = min(p, 0.90)` hasta recuperar calibración).

### Fase 2 (calibración robusta de probabilidad)

1. Entrenar calibrador con **ventana temporal holdout estricta** (sin mezclar pasado/futuro).
2. Comparar en validación: `sigmoid` vs `isotonic` y quedarse con menor ECE (no solo mejor AUC).
3. Guardar en `model_meta.json`:
   - método de calibración elegido,
   - fecha de ajuste,
   - ECE/Brier de calibración,
   - tamaño de muestra utilizada.

### Fase 3 (control por bot + segmentación)

1. Usar semáforo por bot para promoción REAL:
   - verde: n>=30 y gap<10pp,
   - amarillo: n entre 10 y 29,
   - rojo: gap>=15pp o WR reciente <45%.
2. No promover bots en rojo aunque tengan prob puntual alta.
3. Introducir “presupuesto de errores de sobreconfianza” por bot (si acumula X falsos altos en ventana N, bloquear temporalmente).

### Fase 4 (operativa REAL más inteligente)

1. Cuando haya muestra madura, desactivar `REAL_CLASSIC_GATE` en ventanas controladas para permitir umbral adaptativo real.
2. Migrar de gate fijo por probabilidad a gate mixto:
   - `score_final = w1*prob_calibrada + w2*salud_bot + w3*régimen`.
3. Definir criterio de rollback: si cae precisión objetivo por debajo de piso (`IA_TARGET_PRECISION_FLOOR`) en dos checkpoints consecutivos, volver a modo conservador.

## Métricas clave que deben gobernar decisiones

- **Calibración**: ECE, Brier, gap por buckets.
- **Negocio/operación**: precisión @>=85, drawdown por ciclo martingala, falsas altas por bot.
- **Confiabilidad de muestra**: n total cerradas, n por bot, IC95% de winrate por bucket.

## Recomendación concreta para tu pregunta

Para tener una `Prob IA` más real y acertada:

1. **No cambies primero el modelo**; primero sube calidad de muestra cerrada y gobierna por calibración.
2. Usa el pipeline de calibración ya existente, pero seleccionando el calibrador por ECE/Brier (no por intuición).
3. Mantén un guardarraíl anti-sobreconfianza activo hasta que el bucket 90–100% baje su gap a zona aceptable.
4. Recién cuando haya muestra madura, abre la compuerta adaptativa completa para REAL.

En resumen: sí, se puede mejorar bastante la “realidad” de la probabilidad IA, y el camino correcto es **más disciplina de calibración y validación continua** que “más complejidad de modelo”.
