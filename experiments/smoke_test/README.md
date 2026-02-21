# Smoke Test

5-minute smoke test: each agent does 2 discovery requests.

## Safety Controls

- **Jitter:** 0–1500ms random start delay per agent
- **Per-agent concurrency:** max 3
- **Global concurrency:** max 25 in-flight

## Logging

Every request log includes: `run_tag`, `agent_id`, `mode`, `step`, `latency_ms`, `status`

## Output

- `results/week5/exp1/<run_tag>_logs.json`
- `results/week5/exp1/<run_tag>_summary.json`
- `results/week5/exp1/smoke_test_summary.md`

## Usage

```bash
# All 50 consumers, 2 requests each, 5-min cap
python experiments/smoke_test/run_smoke_test.py \
  --agents consumer_001:consumer_050 \
  --requests-per-agent 2 \
  --duration-seconds 300

# Batch A only (10 consumers)
python experiments/smoke_test/run_smoke_test.py \
  --agents consumer_001:consumer_010 \
  --run-tag batch_A

# With consumer health check
python experiments/smoke_test/run_smoke_test.py \
  --consumer-base-url http://1.2.3.4:6001
```
