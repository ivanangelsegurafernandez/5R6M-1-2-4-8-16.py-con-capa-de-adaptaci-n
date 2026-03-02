#!/usr/bin/env python3
"""Analiza patrones repetibles para aumentar la tasa de acierto.

Uso rápido:
  python analisis_patron_ganador.py
  python analisis_patron_ganador.py --top 15 --min-muestras 20 --guardar reporte_patrones.txt

El script:
- Carga un CSV (por defecto dataset_incremental.csv)
- Calcula la tasa base de acierto
- Evalúa reglas por pares de features en extremos (<=Q1 y >=Q3)
- Ordena por lift (WR_regla - WR_base)
- Muestra un resumen claro en consola
"""
from __future__ import annotations

import argparse
import csv
from itertools import combinations
from pathlib import Path
from typing import Callable

DEFAULT_DATASET = "dataset_incremental.csv"
DEFAULT_MIN_MUESTRAS = 30
DEFAULT_TOP = 10

FEATURES = [
    "rsi_9",
    "rsi_14",
    "payout",
    "puntaje_estrategia",
    "volatilidad",
    "breakout",
    "racha_actual",
    "es_rebote",
    "rsi_reversion",
    "cruce_sma",
    "sma_spread",
]


class DataError(Exception):
    """Error de validación/carga de datos."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Detecta patrones ganadores por lift.")
    parser.add_argument(
        "--dataset",
        default=DEFAULT_DATASET,
        help="Ruta al CSV (default: dataset_incremental.csv)",
    )
    parser.add_argument(
        "--min-muestras",
        type=int,
        default=DEFAULT_MIN_MUESTRAS,
        help="Mínimo de muestras por regla para reportar (default: 30)",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=DEFAULT_TOP,
        help="Cantidad de reglas top a mostrar (default: 10)",
    )
    parser.add_argument(
        "--guardar",
        default="",
        help="Ruta opcional para guardar el reporte en texto",
    )
    return parser.parse_args()


def load_rows(path: Path) -> list[dict[str, float]]:
    if not path.exists():
        raise DataError(
            f"No se encontró el dataset: {path}. Ejecuta desde la carpeta del proyecto "
            "o pasa --dataset con la ruta correcta."
        )

    rows: list[dict[str, float]] = []
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise DataError("CSV vacío o sin encabezados.")

        faltantes = [c for c in FEATURES + ["result_bin"] if c not in reader.fieldnames]
        if faltantes:
            raise DataError(f"Faltan columnas requeridas en CSV: {', '.join(faltantes)}")

        for row in reader:
            try:
                rows.append({k: float(v) for k, v in row.items()})
            except (TypeError, ValueError) as exc:
                raise DataError(f"Fila inválida en CSV: {row}") from exc

    if not rows:
        raise DataError("El dataset no tiene filas para analizar.")

    return rows


def quantile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    idx = int((len(ordered) - 1) * q)
    return ordered[idx]


def win_rate(rows: list[dict[str, float]]) -> float:
    return sum(r["result_bin"] for r in rows) / len(rows)


def analyze(rows: list[dict[str, float]], min_muestras: int) -> tuple[float, list[dict[str, float]]]:
    base = win_rate(rows)

    thresholds: dict[str, dict[str, Callable[[float], bool]]] = {}
    for feat in FEATURES:
        vals = [r[feat] for r in rows]
        q1, q3 = quantile(vals, 0.25), quantile(vals, 0.75)
        thresholds[feat] = {
            "<=Q1": lambda x, t=q1: x <= t,
            ">=Q3": lambda x, t=q3: x >= t,
        }

    candidates: list[dict[str, float]] = []
    for f1, f2 in combinations(FEATURES, 2):
        for op1, c1 in thresholds[f1].items():
            for op2, c2 in thresholds[f2].items():
                subset = [r for r in rows if c1(r[f1]) and c2(r[f2])]
                if len(subset) < min_muestras:
                    continue
                wr = win_rate(subset)
                candidates.append(
                    {
                        "n": len(subset),
                        "wr": wr,
                        "lift": wr - base,
                        "rule": f"{f1} {op1} AND {f2} {op2}",
                    }
                )

    candidates.sort(key=lambda x: x["lift"], reverse=True)
    return base, candidates


def build_report(dataset_path: Path, n_rows: int, base: float, top_rules: list[dict[str, float]]) -> str:
    lines = [
        "=== REPORTE: PATRONES GANADORES ===",
        f"Dataset: {dataset_path}",
        f"Filas: {n_rows}",
        f"Win rate base: {base:.2%}",
        "",
    ]

    if not top_rules:
        lines.append("No se encontraron reglas con el mínimo de muestras configurado.")
        lines.append("Tip: prueba bajando --min-muestras (ej: 20).")
        return "\n".join(lines)

    lines.append("Top reglas por lift:")
    for idx, c in enumerate(top_rules, start=1):
        lines.append(
            f"{idx:02d}. {c['rule']} | WR={c['wr']:.2%} | lift={c['lift']:+.2%} | n={int(c['n'])}"
        )

    lines.append("")
    lines.append("Lectura rápida:")
    lines.append("- lift positivo: mejora vs tasa base")
    lines.append("- n alto: patrón más confiable")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    dataset_path = Path(args.dataset).resolve()

    try:
        rows = load_rows(dataset_path)
        base, rules = analyze(rows, min_muestras=args.min_muestras)
    except DataError as err:
        print(f"[ERROR] {err}")
        return 1

    top_rules = rules[: max(1, args.top)]
    report = build_report(dataset_path, len(rows), base, top_rules)
    print(report)

    if args.guardar:
        out_path = Path(args.guardar).resolve()
        out_path.write_text(report + "\n", encoding="utf-8")
        print(f"\nReporte guardado en: {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
