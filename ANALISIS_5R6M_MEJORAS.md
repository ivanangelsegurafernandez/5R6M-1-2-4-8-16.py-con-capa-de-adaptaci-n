# Análisis y plan de mejora para `5R6M-1-2-4-8-16.py`

## Diagnóstico rápido

1. El sistema ya tiene bastantes defensas anti-sobreconfianza (shrinkage, cap en warmup, umbrales y auditoría), pero su efectividad actual está limitada por **muy poca muestra cerrada** para validar calibración real.
2. El último reporte indica sobreconfianza fuerte en el rango 90–100% (prob media 97.3% vs winrate real 54.5%), lo que sugiere que la `Prob IA` todavía no representa bien la probabilidad real observada.
3. La base técnica para calibrar mejor ya existe en el código (calibrador sigmoid/isotonic + auditorías + umbral adaptativo), por lo que la mejora más rentable es **operativa y de gobernanza de datos**, no “cambiar todo el modelo”.

## Evidencia encontrada

- Umbrales y controles anti-sobreconfianza definidos en configuración global (`IA_SHRINK_ALPHA`, límites de warmup y caps).  
- Wrapper explícito de calibración de probabilidad (`ModeloXGBCalibrado`) con opciones `sigmoid` e `isotonic`.  
- Umbral REAL adaptativo implementado con `REAL_CLASSIC_GATE=True`, pero en esta versión **no equivale a 85% fijo**: los pisos base están en torno a 60% (`IA_ACTIVACION_REAL_THR`) y el objetivo dinámico en 70% (`AUTO_REAL_THR`).  
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

1. Cuando haya muestra madura, evaluar en ventanas controladas si conviene seguir con `REAL_CLASSIC_GATE` o migrar a compuerta plenamente adaptativa (sin asumir que hoy esté “fijo en 85%”).
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

---

## Diagnóstico quirúrgico del HUD y lógica estable (sin tocar código aún)

### Secuencia más probable observada

Con la evidencia descrita (token REAL→DEMO, variación de saldo real y cambios en W/L del bot líder), la lectura más consistente es:

1. **Sí hubo entrada REAL previa** en `full50` (o bot campeón vigente en ese instante).
2. **C1 se cerró en pérdida** (saldo real cae y aumenta `PÉRDIDAS` del bot).
3. El sistema marcó **"Próx C2"**, pero **no ejecutó nueva entrada** por bloqueo de elegibilidad/repetición + compuertas de confiabilidad (`reliable=false`, warmup, hard-guard).
4. El HUD mostró simultáneamente mensajes de **señal disponible** y **NO-GO para nuevas entradas**, lo cual es posible si cada panel está leyendo estados de distinta etapa del ciclo.

No es necesariamente “entrada fantasma”; parece más bien **estado arrastrado + paneles desfasados**.

### Las 4 piezas críticas (quién manda realmente)

#### 1) Autorizador de entrada (Entry Authority)
Debe ser una sola decisión atómica por tick:

- `entry_authorized = TRUE` únicamente si pasan TODAS las compuertas de nueva entrada:
  - techo/floor,
  - confirmaciones,
  - trigger,
  - reliable/canary,
  - lock de repetición,
  - token libre.

Si no, `entry_authorized = FALSE` sin ambigüedad.

#### 2) Bloqueador (Block Authority)
No debe “competir” con el autorizador: debe tener precedencia clara.

- Si cualquier bloqueo duro está activo (`reliable=false`, `closed<min`, `anti-repeat`, `token ocupado`, `hard-guard`), se genera:
  - `block_reason_primary` (única causa principal),
  - `block_reason_secondary[]` (causas adicionales),
  - y se fuerza `entry_authorized=FALSE`.

#### 3) Liberador de token (Token Authority)
Separar explícitamente:

- **Estado de posición actual** (`position_state`: NONE/OPEN/CYCLE_WAIT/CLOSED)
- **Permiso de nueva entrada** (`entry_authorized`)

Regla de oro:

- Puedes tener `position_state=OPEN` y a la vez `entry_authorized=FALSE` para nuevas entradas.
- HUD debe decirlo así, en una sola frase de verdad operacional.

#### 4) Panel informativo (HUD Authority)
El HUD no debe recomputar lógica por su cuenta; solo debe pintar un **snapshot único**.

- Introducir concepto de `decision_epoch_id` por tick.
- Cada bloque visual imprime ese mismo `epoch_id`.
- Si un panel muestra otro `epoch_id`, marcar “stale panel”.

Así se elimina la sensación de “semáforo con dos cerebros”.

## Lógica estable e inteligente recomendada (prioriza precisión alta real)

### A. Contrato único de decisión por tick
Publicar un objeto canónico (mentalmente, sin implementar aún):

- `epoch_id`
- `candidate_bot`
- `p_raw`, `p_cal`, `p_oper`
- `roof`, `floor`, `confirm_state`, `trigger_state`
- `reliable_state`, `warmup_state`, `canary_state`
- `anti_repeat_state`
- `token_state`
- `entry_authorized`
- `block_reason_primary`
- `position_state`

Todo el HUD y los eventos deben salir de ese contrato.

### B. Política de probabilidad alta con anti-sobreconfianza
Si quieres que “predomine >90%” sin autoengaño:

1. Mantener **doble umbral**:
   - Umbral de observación (ej. ≥60%) para ranking/contexto.
   - Umbral REAL (dinámico) para ejecución.
2. Si `p_oper >= 90%` pero `reliable=false` o `warmup=true`, tratarlo como **alta convicción no operable** (label: `HI_CONF_BLOCKED`).
3. Activar **penalización por calibración**:
   - si bucket 90–100 tiene gap alto reciente, bajar temporalmente `p_oper` o subir `roof_dynamic`.

Resultado: mantienes sensibilidad a señales fuertes, pero no abres REAL con probabilidad inflada.

### C. Reglas limpias para Martingala C2..C6
Para evitar el caso “Próx C2” + “se omite por repetición” confuso:

- Distinguir dos modos:
  1. **Cycle-locked**: C2..C6 pertenece al mismo bot/idea (permite repetición controlada).
  2. **Fresh-entry**: nueva entrada exige bot distinto (anti-repeat estricto).
- El bloqueo anti-repeat no debe aplicarse igual a ambos modos.
- Mostrar en HUD: `cycle_mode=LOCKED|FRESH`.

### D. Jerarquía de estados legible por humano
Orden de precedencia recomendado en texto HUD:

1. `POSITION` (qué está activo ahora)
2. `ENTRY_PERMISSION` (si puede abrir algo nuevo)
3. `PRIMARY_BLOCK`
4. `NEXT_ACTION` (ej. “esperar C2”, “sin bot elegible”, “token libre”)

Esto evita contradicciones tipo “SEÑAL LISTA + NO-GO” sin contexto.

### E. Métrica de estabilidad operativa (nueva)
Además de AUC/ECE, seguir esta métrica:

- **Consistency Rate HUD** = `% ticks donde todos los paneles comparten el mismo epoch y misma decisión principal`.

Meta mínima: >99%.
Si baja, no escalar exposición REAL aunque la probabilidad suba.

## Diagnóstico final accionable

- Tu hipótesis principal es correcta: el sistema parece mezclar **estado de ciclo activo** con **autorización de nueva entrada** en la visualización.
- La mejora clave no es “subir techo sí/no” aislado, sino **unificar autoridad de decisión + sincronía de HUD + reglas separadas para C2/C6 vs entrada fresca**.
- Solo después de esa limpieza conviene afinar el `roof_dynamic`; de lo contrario, cualquier ajuste de umbral se vuelve difícil de interpretar y fácil de sobreajustar.

## Respuesta directa: ¿los candados están muy duros para invertir más seguido?

### Diagnóstico corto

**Sí, hoy están duros para frecuencia** (especialmente en warmup), pero **no necesariamente están “mal” para riesgo**.

Por lo observado en HUD:

- `reliable=false` + `warmup` está actuando como bloqueo dominante.
- `ROOF` relativamente alto en modo operativo (77–78%) filtra muchas señales aunque el candidato salga “alto” en un tick.
- Anti-repetición está frenando continuidad en C2 cuando la lógica de ciclo no está separada de entrada fresca.

Resultado práctico: el sistema favorece **pocas entradas** y evita sobreoperar, pero también puede perder continuidad útil cuando aparece un candidato fuerte repetido.

### Regla de equilibrio (frecuencia vs calidad)

No conviene “abrir todo” ni dejarlo tan rígido. La forma estable es usar un **perfil por fase**:

1. **Warmup / confiabilidad baja**
   - Mantener candados duros para REAL.
   - Permitir más observación/DEMO para recolectar evidencia.
2. **Transición (muestra intermedia)**
   - Aflojar 1 nivel el techo dinámico solo si mejora la calibración por buckets.
   - Mantener guardia anti-sobreconfianza en 90–100.
3. **Maduro (reliable=true sostenido)**
   - Permitir más frecuencia REAL con compuerta adaptativa y control por bot.

### Cómo saber si aflojar candados sin romper el sistema

Aflojar solo si se cumplen **dos condiciones a la vez**:

- Calibración aceptable (gap en bucket 90–100 controlado).
- Drawdown estable por ciclo (sin deterioro en 2 checkpoints seguidos).

Si una de las dos falla, se vuelve al perfil anterior.

### Propuesta concreta para “más seguidas” sin desorden

1. Mantener `ROOF` actual para entrada fresca, pero crear tratamiento distinto para continuidad:
   - **Fresh-entry**: candado actual (más estricto).
   - **Cycle-locked C2..C6**: candado específico de ciclo (menos penalizado por anti-repeat).
2. Cuando `p_oper >= 90%` y la señal está bloqueada por warmup/reliable, marcar explícitamente `HI_CONF_BLOCKED` (alta convicción, no operable aún).
3. Ajustar por pasos pequeños y medibles (no saltos grandes):
   - Cambios graduales del techo/floor.
   - Evaluación cada +20 cierres.
   - Rollback automático si cae precisión o sube drawdown.

### Conclusión práctica

- **Sí**, para el objetivo de “más inversiones seguidas”, los candados actuales están del lado conservador.
- **Pero** no deben relajarse de golpe: primero separar continuidad de ciclo vs entrada fresca y gobernar por calibración + drawdown.
- La meta correcta no es solo “entrar más”, sino **entrar más cuando la probabilidad alta sea confiable de verdad**.

---

## Correcciones clave tras revisión de evidencia del repo

### 1) El cuello principal no es un "85% pétreo"

Con los parámetros actuales del script principal, el sistema opera con:

- `IA_ACTIVACION_REAL_THR = 0.60`
- `AUTO_REAL_THR = 0.70`
- `REAL_CLASSIC_GATE = True`

Por tanto, el freno dominante observado para nuevas entradas no parece ser un 85% fijo, sino la combinación de:

- `reliable=false`,
- warmup,
- hard-guard,
- y bloqueos de elegibilidad/rotación.

### 2) Riesgo estructural: frescura del modelo vs dataset incremental

Antes de afinar techo/floor, hay que auditar la coherencia de entrenamiento:

- `dataset_incremental.csv` tiene más filas que las usadas por el modelo activo.
- `model_meta.json` declara `rows_total`/`n_samples` bastante menores que el incremental actual.

Esto obliga a validar si:

1. El campeón se reentrena realmente con el incremental vigente.
2. Hay filtros que recortan en exceso antes del fit.
3. El pipeline está promoviendo un modelo con ventana desactualizada.

Sin esa verificación, cualquier tuning de candados puede ser maquillaje sobre un modelo parcial.

### 3) Sobreconfianza: hipótesis plausible, evidencia local limitada

La hipótesis de sobreconfianza en 90–100% es razonable, pero en este repositorio debe tratarse como **hipótesis operativa** hasta consolidar evidencia de cierres por bucket en logs/reporte activo (por ejemplo, cuando `ia_signals_log.csv` tenga cierres útiles y no solo cabecera).

Sí hay evidencia suficiente de prudencia porque el meta actual muestra:

- `reliable=false`,
- AUC/Brier moderados,
- precisión por umbral útil pero aún no robusta para confiar ciegamente en probabilidades extremas.

### 4) Nudo real de frecuencia: C2..C6 tratados como rotación estricta

La lógica actual de martingala para `C2..C6` excluye:

- bots ya usados en la corrida,
- y además `ultimo_bot_real`.

Si no quedan bots nuevos, retorna `None` y omite entrada.

Esto explica de forma directa los casos de:

- “Próx C2”
- junto con “sin bot nuevo elegible / se omite para evitar repetición”.

## Reorden del plan maestro (prioridad recomendada)

### Fase 0 — Frescura del campeón

Primero verificar por qué el modelo operativo usa menos muestra que el incremental disponible y corregir eso (si aplica).

### Fase 1 — Separar "entrada fresca" de "continuidad de ciclo"

- **Fresh-entry**: mantener anti-repeat estricto y candados completos.
- **Cycle-continuation (C2..C6)**: permitir continuidad del mismo bot bajo seguridad dura (saldo/hard-guard/invalidación severa), sin tratarla como entrada nueva normal.

### Fase 2 — Contrato único por tick y HUD sincronizado

Consolidar una sola verdad operativa por `epoch_id` para que todos los paneles muestren el mismo estado y bloqueo principal.

### Fase 3 — Calibración y tuning fino

Recién después: ajuste de `roof_dynamic`, selección de calibrador por ECE/Brier y política de probabilidades altas con control de sobreconfianza.

---

## Mapa real de variables (pipeline actual) y propuesta CORE13 minuto-a-minuto

### 1) ¿Dónde nacen hoy las variables?

**Etapa A — Bots fuente (fulll45..fulll50):**
Cada bot calcula indicadores y persiste una fila enriquecida por trade en `registro_enriquecido_<bot>.csv` con su `CSV_HEADER`. Ahí se originan señales como `rsi_9`, `rsi_14`, `sma_5`, `cruce_sma`, `breakout`, `rsi_reversion`, `racha_actual`, etc.  

**Etapa B — Maestro 5R6M (contrato canónico):**
El maestro define el contrato de features en `FEATURE_NAMES_CORE_13` y lo replica en `INCREMENTAL_FEATURES_V2`, que gobierna validación/escritura/lectura del incremental y entrenamiento.  

**Etapa C — Consolidación:**
`dataset_incremental.csv` es el histórico central tabular para IA, con columnas `features + result_bin`; se usa para construir `X/y` y entrenar/calibrar el campeón.

### 2) ¿Qué es exactamente `dataset_incremental.csv`?

- Es el dataset operativo de entrenamiento del oráculo (no un log visual de HUD).
- Cada fila representa una observación cerrada con etiqueta `result_bin`.
- Esquema canónico: `INCREMENTAL_FEATURES_V2 + result_bin`.
- No multiplica columnas por bot; con más bots crece el número de filas, no el ancho del esquema.

### 3) ¿Qué variables se aprovechan hoy (campeón) y cuáles no?

**Estado real debe leerse siempre desde `model_meta.json` vigente (campo `feature_names`).**

En este snapshot local del repositorio, el campeón usa **3** features:

- `racha_actual`
- `puntaje_estrategia`
- `payout`

No usadas por el campeón de este snapshot (del core de 13):

- `rsi_9`, `rsi_14`, `sma_5`, `sma_spread`, `cruce_sma`, `breakout`, `rsi_reversion`, `volatilidad`, `es_rebote`, `hora_bucket`.

> Nota de gobernanza: en otras corridas/sesiones puede aparecer un campeón con otro set (por ejemplo 6 features). Por eso, el documento debe distinguir entre **estado actual observado** y **propuesta objetivo**, sin mezclarlos.

Además, hay una señal de calidad importante:

- `sma_spread` figura como **ROTA** (dominancia 1.0, `nunique=1`) y aparece en `dropped_features` del meta vigente.
- Si el incremental más reciente muestra variación en `sma_spread`, tratarlo como alerta de consistencia (posible desalineación temporal entre incremental y ventana efectiva de entrenamiento del campeón).

### 4) ¿Dónde se hacen los cambios (archivos/bloques)?

1. **Bots fuente** (`botttt45..50-1-2-4-8-16-32.py`):
   - Cálculo en vivo de nuevas variables.
   - Escritura consistente en `CSV_HEADER` / snapshot por trade.

2. **Maestro 5R6M** (`5R6M-1-2-4-8-16.py`):
   - Contrato: `FEATURE_NAMES_CORE_13`, `INCREMENTAL_FEATURES_V2`.
   - Reparación/validación del incremental (`_canonical_incremental_cols`, `validar_fila_incremental`, `_anexar_incremental_desde_bot_CANON`).

3. **Artefactos de modelo**:
   - Reentreno y guardado atómico de `modelo_xgb.pkl`, `scaler.pkl`, `feature_names.pkl`, `model_meta.json`.

### 5) Propuesta CORE13 v2 (1-minuto friendly)

Mantener las 3 que hoy sí usa el campeón:

1. `racha_actual`
2. `puntaje_estrategia`
3. `payout`

Sustituir las no usadas/menos útiles por 10 features micro-horizonte:

4. `ret_1m`
5. `ret_3m`
6. `ret_5m`
7. `slope_5m`
8. `rv_20`
9. `range_norm`
10. `bb_z`
11. `body_ratio`
12. `wick_imbalance`
13. `micro_trend_persist`

> Nota: en esta corrida el campeón colapsó a 3 features; por eso la propuesta parte de 3 + 10 micro. Si en próximos campeones reaparecen features robustas (p.ej. `breakout`/`es_rebote`), se puede recombinar a 6 + 7.

### 5.1) Estado actual vs propuesta (para evitar confusiones)

- **Estado actual observado (meta vigente):** usar `feature_names` de `model_meta.json` como fuente de verdad.
- **CORE13_v2 aplicado:** contrato ya migrado en maestro; seguir validando desempeño vs campeón previo.
- Cualquier PR de variables debe declarar explícitamente ambos bloques para no mezclar diagnóstico con intención de diseño.

### 6) Plan de migración sin romper producción

1. **Shadow logging** de las 10 nuevas en bots (sin cambiar aún el contrato core).
2. **Auditoría de salud** (nunique, dominancia, faltantes, estabilidad por ventana temporal).
3. **Contrato v2 activo:** auditar estabilidad de `CORE13_v2` (calibración, drawdown, salud de features) y preparar rollback a v1 si degrada.
4. **Incremental limpio v2** + reentreno + canary controlado.
5. **Promoción** solo si mejora calibración/precisión sin empeorar drawdown.

### 7) Respuesta directa (estado de implementación)

Actualización de estado:

- **Sí se ejecutó la migración del contrato de features CORE13 en el maestro** (`FEATURE_NAMES_CORE_13` / `INCREMENTAL_FEATURES_V2`) hacia el set scalping propuesto.
- Se mantuvo compatibilidad con datos legacy mediante backfill/derivación de las nuevas features desde columnas históricas cuando faltan.
- La lógica operativa/HUD/martingala previa se conserva; el cambio de este paso fue específicamente de contrato/ingeniería de variables.

### 8) Qué se mantiene igual y qué se reemplaza (enfoque scalping)

Regla: **mantener lo que hoy aporta en el campeón** y reemplazar solo lo no usado/no robusto.

#### Se mantiene (estado actual observado en este snapshot)

1. `racha_actual`
2. `puntaje_estrategia`
3. `payout`

#### Se reemplaza (candidatas del core actual con bajo/no uso en campeón)

4. `rsi_9`              -> `ret_1m`
5. `rsi_14`             -> `ret_3m`
6. `sma_5`              -> `ret_5m`
7. `sma_spread`         -> `slope_5m`
8. `cruce_sma`          -> `rv_20`
9. `breakout`           -> `range_norm`
10. `rsi_reversion`     -> `bb_z`
11. `volatilidad`       -> `body_ratio`
12. `es_rebote`         -> `wick_imbalance`
13. `hora_bucket`       -> `micro_trend_persist`

> Nota operativa: mapeo ya aplicado en maestro; mantener shadow/auditoría/canary para validar que v2 supere o iguale a v1.
