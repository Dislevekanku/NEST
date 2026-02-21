# Experiment 1: Discovery Efficiency

**Goal:** Measure discovery friction reduction when using Agent Facts + Data Facts URL vs manual endpoint knowledge.

## Setup

- **Baseline:** Agent-only discovery (manual endpoint knowledge) — direct `GET` to dataset URL. 1 step.
- **Treatment:** Agent Facts + Data Facts URL — registry → `data_facts_url` → Data Facts → dataset. 3 steps.
- **Dataset:** Public API (stock ticker via Data Facts; configurable).

## Metrics

- Time-to-first-data (mean, p50, p95 in seconds)
- Number of failed lookups
- Success rate (%)
- Steps per query (1 vs 3)

## Prerequisites

1. **Dataset server** serving Data Facts + dataset (e.g. finance feed agent or `DatasetServer` + `StockDatasetProvider` on port 8000).
2. **Registry** (e.g. `http://registry.chat39.com:6900`) with at least one agent registered with `data_facts_url`.
3. For **EC2 runs:** use `config_ec2.json`; point `dataset_endpoint` and `data_facts_url` at Finance Feed IP (e.g. `http://54.172.251.235:8000/...`).

## Usage

```bash
# From NEST root
cd experiments/exp1_discovery_efficiency

# Debug run (N=50, verbose)
python run.py --N 50 --mode both --debug

# Record run (N=200)
python run.py --N 200 --mode both

# Sweep N=50 and N=200 (table + time-to-data vs N plot)
python run.py --sweep 50,200

# Use EC2 config
python run.py --sweep 50,200 --config config_ec2.json

# Multi-agent ecosystem (finance + weather)
export ECOSYSTEM_IP=<deployed-ecosystem-IP>
python run.py --sweep 50,200 --config config_ecosystem.json

# 50-agent ecosystem (6 data + 44 non-data)
python run.py --sweep 50,200 --config config_ecosystem_50.json

# Paper-grade 50-agent scale run (N=50 first pass, N=200 paper run)
# Uses config_ecosystem_50.json; writes exp1_scale_50agents_* + exp1_raw.jsonl
export ECOSYSTEM_IP=<deployed-ecosystem-IP>
python run.py --scale-50
```

## Deliverables

| Deliverable | Location |
|-------------|----------|
| **Table: Baseline vs Data Facts** | `results/exp1_*_table.md` |
| **Plot: time-to-data vs N** | `results/exp1_*_plot.png` |
| **Short results summary (5–7 bullets)** | `results/exp1_*_summary.md` |
| **Structured log** | `results/exp1_*_results.json` |

Latest sweep (N=50, 200): `results/exp1_sweep_50_200_*` (or timestamped `exp1_sweep_50_200_YYYYMMDD_HHMMSS_*`).

### Scale-50 (paper-grade) run

With `--scale-50`, the following fixed-name deliverables are written in addition to the timestamped ones:

| Deliverable | Location |
|-------------|----------|
| **Table** | `results/exp1_scale_50agents_table.md` |
| **Plot** | `results/exp1_scale_50agents_plot.png` |
| **Summary (5–7 bullets)** | `results/exp1_scale_50agents_summary.md` |
| **Raw event log (JSONL)** | `results/exp1_raw.jsonl` |
| **Archived raw log** | `results/exp1_raw_YYYYMMDD_HHMMSS.jsonl` |

## Outputs

- `results/exp1_*_results.json` — structured log
- `results/exp1_*_table.md` — Baseline vs Data Facts table
- `results/exp1_*_plot.png` — time-to-first-data vs N (`plot_exp1.py` or `run.py --dry-run`)
- `results/exp1_*_summary.md` — short results summary (5–7 bullets)

## Dry-run (no HTTP)

```bash
python run.py --dry-run
```

Emits mock results for N=50,200 (table, plot, summary) without hitting registry or dataset endpoints.

```bash
python run.py --scale-50 --dry-run
```

Emits the same plus `exp1_scale_50agents_*` and `exp1_raw.jsonl` with mock query events.
