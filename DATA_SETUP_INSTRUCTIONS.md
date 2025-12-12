# Creating HR Dataset for NEST Ecosystem

## Quick Setup (Already Done ✅)

The HR dataset has been created at: `NEST/data/hr.csv`

## Manual Setup Instructions

If you need to recreate or modify the dataset:

### Steps:

1. **Navigate to NEST directory:**
   ```bash
   cd NEST
   ```

2. **Create data directory (if it doesn't exist):**
   ```bash
   # Windows PowerShell
   if (-not (Test-Path "data")) { New-Item -ItemType Directory -Path "data" }
   
   # Linux/Mac
   mkdir -p data
   ```

3. **Create the HR dataset:**
   ```bash
   # Windows PowerShell
   # Create file: data/hr.csv
   
   # Linux/Mac
   nano data/hr.csv
   ```

4. **Paste this EXACT content:**
   ```csv
   employee_id,department,salary,years_at_company
   1001,Engineering,145000,5
   1002,Sales,92000,2
   1003,HR,86000,4
   1004,Marketing,78000,1
   ```

5. **Save the file:**
   - **Windows**: Save in your editor
   - **Linux/Mac**: CTRL+O, ENTER, CTRL+X

## Using the Dataset

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
  "data/hr.csv"  # <-- 12th parameter: DATA_PATH
```

## Dataset Structure

The HR dataset contains:
- **4 employees** across different departments
- **Columns:**
  - `employee_id`: Unique identifier (1001-1004)
  - `department`: Engineering, Sales, HR, Marketing
  - `salary`: Annual salary (78k-145k)
  - `years_at_company`: Years of service (1-5)

## Purpose

This dataset allows the HR agent to:
- Demonstrate "having data" 
- Respond to questions based on actual employee data
- Show how agents can use attached datasets

## File Location in NEST

```
NEST/
├── data/
│   ├── hr.csv          ← HR dataset (ready to use)
│   └── README.md       ← Data directory documentation
├── examples/
│   └── nanda_agent.py ← Agent that loads data
└── scripts/
    └── aws-single-agent-deployment.sh ← Deployment with DATA_PATH
```

## Next Steps

1. ✅ Dataset created at `data/hr.csv`
2. ✅ Agent can load it via `DATA_PATH=data/hr.csv`
3. 🔜 Step 4: Expose data via MCP tools (get_row_count, query_data, etc.)

