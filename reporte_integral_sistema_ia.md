# Reporte Integral de Salud IA

Generado UTC: `2026-02-28T00:03:22.245127+00:00`

## 1) Calibración real de probabilidades
- Señales cerradas: **5**
- Precisión @>=70%: **80.0%** (n=5)
- Precisión @>=85%: **80.0%** (n=5)
- ⚠️ Muestra cerrada muy baja: estas precisiones son orientativas, no concluyentes.

## 2) Desalineación Prob IA vs hitrate por bot (last_n=40)
| Bot | WR last40 (csv) | n señales IA | Hit last40 (señales) | Prob media last40 (señales) | Gap Prob-Hit señales | Gap Prob-WR csv | Muestra señales |
|---|---:|---:|---:|---:|---:|---:|---|
| fulll45 | 50.0% | 0 | N/A | N/A | N/A | N/A | BAJA(<5) |
| fulll46 | 47.5% | 0 | N/A | N/A | N/A | N/A | BAJA(<5) |
| fulll47 | 57.5% | 1 | 100.0% | 90.7% | N/A | N/A | BAJA(<5) |
| fulll48 | 52.5% | 1 | 0.0% | 95.1% | N/A | N/A | BAJA(<5) |
| fulll49 | 67.5% | 0 | N/A | N/A | N/A | N/A | BAJA(<5) |
| fulll50 | 60.0% | 3 | 100.0% | 89.8% | N/A | N/A | BAJA(<5) |

## 3) Calibración por rangos de probabilidad
| Rango Prob IA | n | Prob media | Winrate real | IC95% winrate | Gap (Prob-Winrate) |
|---|---:|---:|---:|---:|---:|
| 50-60% | 0 | N/A | N/A | N/A | N/A |
| 60-70% | 0 | N/A | N/A | N/A | N/A |
| 70-80% | 0 | N/A | N/A | N/A | N/A |
| 80-90% | 2 | 86.2% | 100.0% | [34.2%, 100.0%] | -13.8% |
| 90-100% | 3 | 94.2% | 66.7% | [20.8%, 93.9%] | 27.5% |

## 4) Capa adaptativa sugerida (EWMA + umbral dinámico)
- Umbral base: **85.0%**
- Umbral dinámico sugerido: **87.0%**
- Salud global EWMA bots: **N/A**
- EWMA usada para umbral: **NO** (bots maduros: 0/2)
- Modo: **solo sugerencia (no automatizar)** | confianza: **low**
- Cobertura mínima para automatizar: closed>=20 y n(90-100)>=8; actual: closed=5, n90=3
- Razones: muestra_insuficiente_para_automatizar, sobreconfianza_alta_90_100, salud_ewma_solo_informativa_por_baja_muestra

| Bot | n señales | Muestra madura | WR crudo | IC95% WR | EWMA acierto | EWMA penalización falsas altas | Salud bot |
|---|---:|---|---:|---:|---:|---:|---:|
| fulll47 | 1 | NO | 100.0% | [20.7%, 100.0%] | 100.0% | 0.0% | 100.0% |
| fulll48 | 1 | NO | 0.0% | [0.0%, 79.3%] | 0.0% | 100.0% | 0.0% |
| fulll50 | 3 | NO | 100.0% | [43.8%, 100.0%] | 100.0% | 0.0% | 100.0% |

## 5) Guía operativa inmediata (shadow mode)
- Compuerta operativa actual: **85.0%**
- Umbral sugerido en sombra: **87.0%**
- Aplicar solo en sombra: **SI**
- Bots sin señales IA: fulll45, fulll46, fulll49
- Bots con muestra baja (<8): fulll47, fulll48, fulll50
- Focos amarillos: decisiones_en_shadow_mode, falta_runtime_log
- Próximo checkpoint: closed>=20, n(90-100)>=8

## 6) Salud de ejecución (auth/ws/timeout)
- No auditado en este run (falta `--runtime-log`).

## 7) Recomendación de cuándo correr este programa
- **Recomendado siempre**: al iniciar sesión y luego cada 30-60 min.
- **Corte de calidad fuerte**: después de cada bloque de +20 cierres nuevos.
- **Punto mínimo para decisiones estructurales**:
  - ✅ n_samples>=250
  - ❌ closed_signals>=80
  - ❌ reliable=true
  - ❌ auc>=0.53
- Ready for full diagnosis: **False**

## 8) Qué falta corregir si no está “bien”
- Nota: `Gap Prob-Hit señales` usa SOLO señales cerradas en `ia_signals_log.csv` y puede diferir de `WR last40 (csv)` del bot.
- Gaps por bot se publican solo si `n señales IA >= 5` para evitar conclusiones con muestra mínima.
- Si `precision@85` baja o n es pequeño: recalibrar/proteger compuerta.
- Si gap Prob-Hit por bot es alto: bajar exposición o bloquear bot temporalmente.
- EWMA por bot con n bajo debe leerse como semáforo blando; evitar castigos duros hasta tener muestra madura.
- Si auth/ws/timeouts suben: estabilizar conectividad antes de evaluar modelo.
- Si WHY-NO se concentra en `trigger_no`/`confirm_pending`: revisar timing de señales y trigger.
