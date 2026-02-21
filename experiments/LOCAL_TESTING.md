# Local Testing (No Deploy): 50-Agent Ecosystem + Exp 1 & 2

Test the 50-agent ecosystem locally, then run Experiment 1 and Experiment 2 and redo results.

## 1. Start local registry (terminal 1)

```bash
cd NEST
python experiments/local_registry.py
```

Runs Flask on **:6900** (or `LOCAL_REGISTRY_PORT`). Leave it running.

## 2. Start 50-agent ecosystem (terminal 2)

```bash
cd NEST
set REGISTRY_URL=http://localhost:6900
set PUBLIC_URL=http://localhost:8000
set DATA_SERVER_PORT=8000
set CONFIG_PATH=%CD%\experiments\ecosystem\config_50_agents.json
python experiments/ecosystem/run_ecosystem.py
```

PowerShell:

```powershell
$env:REGISTRY_URL="http://localhost:6900"; $env:PUBLIC_URL="http://localhost:8000"; $env:DATA_SERVER_PORT="8000"; $env:CONFIG_PATH="$PWD\experiments\ecosystem\config_50_agents.json"; python experiments/ecosystem/run_ecosystem.py
```

Runs MultiDatasetServer on **:8000**, registers 50 agents (6 data, 44 non-data) with the local registry. Leave it running.

## 3. Run Exp 1 and Exp 2 (terminal 3)

```bash
cd NEST
python experiments/run_exp1_exp2_only.py
```

Use `--quick` for a faster Exp 1 sweep (N=5,10):

```bash
python experiments/run_exp1_exp2_only.py --quick
```

## 4. Results

- **Exp 1:** `experiments/exp1_discovery_efficiency/results/` — `*_results.json`, `*_table.md`, `*_plot.png`, `*_summary.md`.
- **Exp 2:** `experiments/exp2_freshness_correctness/results/` — `*_results.json`, `*_stale_vs_detected_table.md`, `*_error_rate_comparison.png`, `*_interpretation.md`.

## One-shot runner (optional)

To start registry + ecosystem, run experiments, then stop services automatically:

```bash
python experiments/run_local_experiments.py
python experiments/run_local_experiments.py --quick
```

Requires registry and ecosystem to stay up long enough for Exp 1 (HTTP calls). If it times out, use the manual flow above.

## Verify

- Registry: `http://localhost:6900/health`
- Ecosystem: `http://localhost:8000/health`
- Data Facts: `http://localhost:8000/data_facts/public_stock_ticker.json`
