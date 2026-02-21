# Experiment 4: Local Security & Auth

**Objectives:** Validate private/semi-private access behavior; produce measurable security metrics.

## Design

- **Agent → Gateway → DB** (simulated in-process; no network).
- **Flows:**
  1. **Owner agent:** Fetches data with owner token → passes result. Measures success rate and auth latency.
  2. **Inquiry agent:** Fetches data using short-lived credentials. Same metrics.
- **Token scenarios:** Valid, expired, malformed (bad signature / corrupted payload).
- **Metrics:** Auth success %, mean auth latency (ms), error counts by failure mode.

## Prerequisites

```bash
pip install PyJWT
```

## Usage

```bash
cd experiments/exp4_security_auth
python run.py [--config config.json] [--out-dir results]
```

## Deliverables

| Deliverable | Path |
|-------------|------|
| Structured results | `results/exp4_security_auth_results.json` |
| Table (flow × scenario → success %, latency) | In results JSON + summary markdown |
| Findings (3–4 bullets) | `results/exp4_security_auth_findings.md` |
