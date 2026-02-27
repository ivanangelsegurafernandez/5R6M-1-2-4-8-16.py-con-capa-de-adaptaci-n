# Reporte Integral de Salud IA

Generado UTC: `2026-02-27T23:27:37.889968+00:00`

## 1) Calibración real de probabilidades
- Señales cerradas: **12**
- Precisión @>=70%: **58.3%** (n=12)
- Precisión @>=85%: **58.3%** (n=12)
- ⚠️ Muestra cerrada muy baja: estas precisiones son orientativas, no concluyentes.

## 2) Desalineación Prob IA vs hitrate por bot (last_n=40)
| Bot | WR last40 (csv) | n señales IA | Hit last40 (señales) | Prob media last40 (señales) | Gap Prob-Hit señales | Gap Prob-WR csv | Muestra señales |
|---|---:|---:|---:|---:|---:|---:|---|
| fulll45 | 45.0% | 3 | 66.7% | 92.5% | N/A | N/A | BAJA(<5) |
| fulll46 | 50.0% | 2 | 50.0% | 97.4% | N/A | N/A | BAJA(<5) |
| fulll47 | 55.0% | 2 | 50.0% | 98.9% | N/A | N/A | BAJA(<5) |
| fulll48 | 55.0% | 1 | 0.0% | 98.3% | N/A | N/A | BAJA(<5) |
| fulll49 | 40.0% | 0 | N/A | N/A | N/A | N/A | BAJA(<5) |
| fulll50 | 55.0% | 4 | 75.0% | 97.5% | N/A | N/A | BAJA(<5) |

## 3) Calibración por rangos de probabilidad
| Rango Prob IA | n | Prob media | Winrate real | Gap (Prob-Winrate) |
|---|---:|---:|---:|---:|
| 50-60% | 0 | N/A | N/A | N/A |
| 60-70% | 0 | N/A | N/A | N/A |
| 70-80% | 0 | N/A | N/A | N/A |
| 80-90% | 1 | 88.0% | 100.0% | -12.0% |
| 90-100% | 11 | 97.3% | 54.5% | 42.8% |

## 4) Capa adaptativa sugerida (EWMA + umbral dinámico)
- Umbral base: **85.0%**
- Umbral dinámico sugerido: **89.0%**
- Salud global EWMA bots: **53.0%**
- Razones: sobreconfianza_alta_90_100

| Bot | n señales | EWMA acierto | EWMA penalización falsas altas | Salud bot |
|---|---:|---:|---:|---:|
| fulll45 | 3 | 75.0% | 25.0% | 66.2% |
| fulll46 | 2 | 75.0% | 25.0% | 66.2% |
| fulll47 | 2 | 75.0% | 25.0% | 66.2% |
| fulll48 | 1 | 0.0% | 100.0% | 0.0% |
| fulll50 | 4 | 75.0% | 25.0% | 66.2% |

## 5) Salud de ejecución (auth/ws/timeout)
- No auditado en este run (falta `--runtime-log`).

## 6) Recomendación de cuándo correr este programa
- **Recomendado siempre**: al iniciar sesión y luego cada 30-60 min.
- **Corte de calidad fuerte**: después de cada bloque de +20 cierres nuevos.
- **Punto mínimo para decisiones estructurales**:
  - ✅ n_samples>=250
  - ❌ closed_signals>=80
  - ❌ reliable=true
  - ❌ auc>=0.53
- Ready for full diagnosis: **False**

## 7) Qué falta corregir si no está “bien”
- Nota: `Gap Prob-Hit señales` usa SOLO señales cerradas en `ia_signals_log.csv` y puede diferir de `WR last40 (csv)` del bot.
- Gaps por bot se publican solo si `n señales IA >= 5` para evitar conclusiones con muestra mínima.
- Si `precision@85` baja o n es pequeño: recalibrar/proteger compuerta.
- Si gap Prob-Hit por bot es alto: bajar exposición o bloquear bot temporalmente.
- Si auth/ws/timeouts suben: estabilizar conectividad antes de evaluar modelo.
- Si WHY-NO se concentra en `trigger_no`/`confirm_pending`: revisar timing de señales y trigger.
