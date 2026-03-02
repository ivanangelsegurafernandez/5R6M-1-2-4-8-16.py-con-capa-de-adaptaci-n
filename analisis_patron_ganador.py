#!/usr/bin/env python3
"""Analiza patrones repetibles para aumentar la tasa de acierto.

Usa dataset_incremental.csv y reporta reglas simples con mejor lift vs baseline.
"""
from __future__ import annotations

import csv
from itertools import combinations

DATASET = "dataset_incremental.csv"
MIN_MUESTRAS_REGLA = 30


def load_rows(path: str):
    rows = []
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({k: float(v) for k, v in row.items()})
    return rows


def quantile(values, q: float) -> float:
    ordered = sorted(values)
    idx = int((len(ordered) - 1) * q)
    return ordered[idx]


def win_rate(rows):
    return sum(r["result_bin"] for r in rows) / len(rows) if rows else 0.0


def main():
    rows = load_rows(DATASET)
    base = win_rate(rows)
    print(f"Filas: {len(rows)}")
    print(f"Win rate base: {base:.2%}\n")

    features = [
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

    thresholds = {}
    for feat in features:
        vals = [r[feat] for r in rows]
        q1, q3 = quantile(vals, 0.25), quantile(vals, 0.75)
        thresholds[feat] = {
            "<=q1": lambda x, t=q1: x <= t,
            ">=q3": lambda x, t=q3: x >= t,
        }

    candidates = []
    for f1, f2 in combinations(features, 2):
        for op1, c1 in thresholds[f1].items():
            for op2, c2 in thresholds[f2].items():
                subset = [r for r in rows if c1(r[f1]) and c2(r[f2])]
                if len(subset) < MIN_MUESTRAS_REGLA:
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
    print("Top reglas por lift:")
    for c in candidates[:10]:
        print(
            f"- {c['rule']}: WR={c['wr']:.2%}, lift={c['lift']:+.2%}, n={c['n']}"
        )


if __name__ == "__main__":
    main()
