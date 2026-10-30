"""M9: one chart for the README - test accuracy of each version with its 95% confidence interval.

Run from the project folder (after harness/stats.py):
    .venv/bin/python harness/chart.py      # writes docs/accuracy_ci.png
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent
LABELS = {"A": "A. No search", "B": "B. Basic search", "C": "C. Smart search", "D": "D. Search + table map",
          "E": "E. Agent", "E_memory": "E. Agent + example memory"}
BLUE, INK, MUTED, GRID, SURFACE = "#2a78d6", "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"


def main():
    summary = json.loads((PROJECT / "results" / "final_summary.json").read_text())["questions"]
    names = [n for n in LABELS if n in summary][::-1]          # A at the top
    fig, ax = plt.subplots(figsize=(7, 3.4), facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    for y, name in enumerate(names):
        s = summary[name]
        ax.plot([s["ci_low"] * 100, s["ci_high"] * 100], [y, y], color=BLUE, linewidth=2, solid_capstyle="round")
        ax.plot(s["accuracy"] * 100, y, "o", color=BLUE, markersize=8, markeredgecolor=SURFACE, markeredgewidth=2)
        ax.text(s["ci_high"] * 100 + 1.2, y, f"{s['accuracy'] * 100:.1f}%", va="center", fontsize=9, color=INK)
    ax.axvline(75, color=MUTED, linewidth=1, linestyle="--")
    ax.text(75.5, len(names) - 0.45, "target 75%", fontsize=8, color=MUTED)
    ax.set_yticks(range(len(names)), [LABELS[n] for n in names], fontsize=9, color=INK)
    ax.set_xlim(40, 100)
    ax.set_xlabel("Execution accuracy on 80 test questions, 3 runs (dot = mean, line = 95% CI)", fontsize=8, color=MUTED)
    ax.tick_params(axis="x", colors=MUTED, labelsize=8)
    ax.tick_params(axis="y", length=0)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ["top", "right", "left"]:
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    fig.tight_layout()
    out = PROJECT / "docs" / "accuracy_ci.png"
    out.parent.mkdir(exist_ok=True)
    fig.savefig(out, dpi=160)
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
