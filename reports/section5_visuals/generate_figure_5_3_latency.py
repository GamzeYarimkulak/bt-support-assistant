# -*- coding: utf-8 -*-
"""Generate Figure 5.3: retrieval latency comparison."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


OUTPUT_PATH = Path(__file__).with_name("sekil_5_3_sorgu_gecikme_dagilimi.png")

METHODS = [
    "BM25",
    "Embedding",
    "Sabit hibrit\n(α = 0,5)",
    "Dinamik hibrit",
]

LATENCIES = [0.2309, 0.0236, 0.2717, 0.2745]
COLORS = ["#6b7280", "#3b82f6", "#14b8a6", "#0f766e"]


def format_decimal(value: float) -> str:
    return f"{value:.4f}".replace(".", ",")


def main() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": "#475569",
            "axes.labelcolor": "#111827",
            "xtick.color": "#1f2937",
            "ytick.color": "#334155",
        }
    )

    x = np.arange(len(METHODS))
    fig, ax = plt.subplots(figsize=(10.5, 5.4), dpi=180)

    bars = ax.bar(
        x,
        LATENCIES,
        width=0.58,
        color=COLORS,
        edgecolor="#1f2937",
        linewidth=0.6,
    )

    ax.set_title(
        "Retrieval Yöntemlerinin Ortalama Sorgu Gecikmeleri",
        fontsize=14,
        fontweight="bold",
        pad=14,
    )
    ax.set_ylabel("Ortalama gecikme (saniye)", fontsize=11)
    ax.set_xticks(x)
    ax.set_xticklabels(METHODS, fontsize=10)
    ax.set_ylim(0, 0.32)
    ax.grid(axis="y", color="#dbe4ec", linewidth=0.8, alpha=0.85)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    for bar, value in zip(bars, LATENCIES):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + 0.008,
            f"{format_decimal(value)} sn",
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
            color="#111827",
        )

    fig.tight_layout()
    fig.savefig(OUTPUT_PATH, bbox_inches="tight")
    plt.close(fig)
    print(OUTPUT_PATH.resolve())


if __name__ == "__main__":
    main()
