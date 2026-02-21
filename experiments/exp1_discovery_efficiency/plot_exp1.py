#!/usr/bin/env python3
"""Generate Experiment 1 plot: time-to-first-data vs N (Baseline vs Treatment)."""
from pathlib import Path

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:
    print("matplotlib required: pip install matplotlib")
    raise SystemExit(1)

# Data: N=50,200 × Baseline vs Treatment (mean TTD seconds)
ns = [50, 200]
baseline = [0.120, 0.130]
treatment = [0.380, 0.400]

fig, ax = plt.subplots()
x = range(len(ns))
w = 0.35
ax.bar([i - w / 2 for i in x], baseline, width=w, label="Baseline", color="#2ecc71")
ax.bar([i + w / 2 for i in x], treatment, width=w, label="Treatment (Data Facts)", color="#3498db")
ax.set_xticks(x)
ax.set_xticklabels([str(n) for n in ns])
ax.set_ylabel("Mean time-to-first-data (seconds)")
ax.set_xlabel("N (number of queries)")
ax.set_title("Experiment 1: Discovery Efficiency — Time-to-First-Data vs N")
ax.legend()
fig.tight_layout()
out = Path(__file__).parent / "results" / "exp1_sweep_50_200_plot.png"
out.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(out, dpi=120)
plt.close()
print(f"Wrote {out}")
