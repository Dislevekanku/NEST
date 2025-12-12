# NEST Data Directory

This directory contains sample datasets that can be attached to NEST agents via the `DATA_PATH` environment variable.

## HR Dataset

**File:** `hr.csv`

A simple HR dataset with employee information:
- `employee_id`: Unique employee identifier
- `department`: Department name (Engineering, Sales, HR, Marketing)
- `salary`: Annual salary
- `years_at_company`: Years of service

## Usage

### Local Testing

```bash
# From NEST directory
DATA_PATH=data/hr.csv python examples/nanda_agent.py
```

### AWS Deployment

```bash
bash scripts/aws-single-agent-deployment.sh \
  "hr-agent" \
  "sk-ant-xxxxx" \
  "HR Assistant" \
  "human resources" \
  "HR specialist" \
  "I help with HR questions and employee data" \
  "HR,employee data,payroll,benefits" \
  "http://registry.chat39.com:6900" \
  "6000" \
  "us-east-1" \
  "t3.small" \
  "data/hr.csv"  # <-- DATA_PATH parameter
```

### On Deployed Instance

The data file will need to be available on the EC2 instance. Options:

1. **Include in repository** (current approach):
   - Data is in the repo, so it's available after `git clone`
   - Use path: `data/hr.csv` (relative to cloned repo)

2. **Upload separately**:
   - Upload to S3 and download in user-data script
   - Or mount EBS volume with data
   - Or use a data URL

## Adding More Datasets

To add more sample datasets:

1. Create CSV or JSON file in this directory
2. Update this README with dataset description
3. Use `DATA_PATH=data/your_file.csv` when deploying

## File Format

- **CSV**: Must have header row, comma-separated
- **JSON**: Must be valid JSON (object or array)

The agent will automatically detect the format based on file extension.

