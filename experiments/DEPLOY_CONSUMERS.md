# Deploy All 50 Consumers + Smoke Test

## Batch Deployment

| Batch | Consumers | Ports |
|-------|-----------|-------|
| A | consumer_001 .. consumer_010 | 6001-6010 |
| B | consumer_011 .. consumer_025 | 6011-6025 |
| C | consumer_026 .. consumer_050 | 6026-6050 |

## Option 1: Full Deploy (EC2 with consumers)

Deploy providers + 50 consumers on one EC2:

```powershell
cd NEST\scripts
$env:SECURITY_GROUP_ID = (aws ec2 describe-security-groups --group-names "nanda-finance-consumer-agents" --region us-east-1 --query 'SecurityGroups[0].GroupId' --output text 2>$null)
.\deploy_ecosystem_50.ps1 -ConfigName "config_manifest_v1.json" -WithConsumers
```

Wait ~2 min, then run smoke test:

```powershell
$env:ECOSYSTEM_IP = "<public-ip>"
python experiments/smoke_test/run_smoke_test.py `
  --agents consumer_001:consumer_050 `
  --requests-per-agent 2 `
  --duration-seconds 300 `
  --consumer-base-url "http://$env:ECOSYSTEM_IP:6001"
```

## Option 2: Batch Deploy + Smoke (local runner)

If consumers run locally or on a known host:

```powershell
$env:CONSUMER_HOST = "127.0.0.1"   # or EC2 public IP
.\deploy_consumers_batches.ps1
```

This runs:
- Batch A: start 10 consumers, 5-min smoke test
- Batch B: start 15 more, 5-min smoke test  
- Batch C: start 25 more, 5-min smoke test

## Safety Controls

- **Jitter:** 0–1500ms random start delay per agent
- **Per-agent concurrency:** max 3
- **Global concurrency:** max 25 in-flight

## Outputs

- `results/week5/exp1/<run_tag>_logs.json`
- `results/week5/exp1/<run_tag>_summary.json`
- `results/week5/exp1/smoke_test_summary.md`
