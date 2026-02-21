# Alignment → Lock Scope → Kill Cloud

**Date locked:** 2026-02-08  
**Goal:** Lock exact experiment set for paper; shift fully to local execution; remove infra distractions.

---

## Final experiment list (no new experiments after lock)

| # | Experiment | Status | Notes |
|---|------------|--------|------|
| **Exp 1** | Discovery efficiency (baseline vs registry → Data Facts → dataset) | ✅ Frozen | N=50, 200; local registry + local or mock ecosystem |
| **Exp 2** | Freshness / TTL correctness | ✅ In scope | Stale vs detected, error-rate comparison |
| **Exp 3** | Integrity / corruption detection | ✅ In scope | Checksum / security relevance |
| **Exp 4** | Local Security & Auth (JWT) | ✅ In scope | Agent → Gateway → DB; success %, auth latency, expired/malformed token handling; deliverable: exp4_security_auth_results.json + table + findings |

---

## Execution model: local only

- **Registry:** `experiments/local_registry.py` (http://localhost:6900). No dependency on registry.chat39.com for paper runs.
- **Ecosystem:** Local multi-dataset server via `experiments/ecosystem/run_ecosystem.py` with `config_50_agents.json`, `REGISTRY_URL=http://localhost:6900`, `PUBLIC_URL=http://localhost:8000`. No EC2.
- **Exp 1 / 2 / 3:** Use `config_ecosystem_50_local.json` (or equivalent) with `registry_url: http://localhost:6900` and local dataset endpoints.

---

## Kill cloud

- **EC2:** Terminate all NANDA-related instances (do not leave stopped). Use `scripts/terminate_nanda_ec2.ps1` or the AWS CLI commands in this doc.
- **No new deploys** for paper; no reliance on 18.234.53.227 or any other cloud IP in experiment configs for the locked set.

---

## Clean up experiment folder

See [Clean up checklist](#clean-up-checklist) below. Optional: remove or archive deploy reports, cloud-only configs, and obsolete IP references so the repo is clearly local-first.

---

## Clean up checklist

- [ ] **Terminate all NANDA EC2 instances** (run `scripts/terminate_nanda_ec2.ps1` or CLI below).
- [ ] (Optional) Archive or remove `experiments/ecosystem/deploy_report.json` if it references cloud IPs you no longer need.
- [ ] (Optional) Keep `config_ecosystem_50.json` as reference but use `config_ecosystem_50_local.json` for all runs.
- [ ] (Optional) Add to `.cursorignore` or docs: “Paper runs use local registry + local ecosystem only.”

---

## Terminate NANDA EC2 instances (PowerShell)

From NEST repo (AWS CLI configured):

```powershell
cd "c:\Users\disle\OneDrive\Documents\projects\Nanda\NEST\scripts"
.\terminate_nanda_ec2.ps1
```

Or manually (us-east-1):

```powershell
# List instance IDs with NANDA project tag (running or stopped)
aws ec2 describe-instances --region us-east-1 --filters "Name=tag:Project,Values=NANDA-Ecosystem-50,NANDA-Ecosystem" "Name=instance-state-name,Values=running,stopped" --query "Reservations[].Instances[].InstanceId" --output text

# Terminate (paste the space-separated instance IDs from above)
aws ec2 terminate-instances --region us-east-1 --instance-ids <INSTANCE_IDS>
```

Replace `<INSTANCE_IDS>` with the actual IDs (e.g. `i-0abc123 i-0def456`).
