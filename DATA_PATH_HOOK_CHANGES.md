# DATA_PATH Hook Implementation - Step 2

## Summary
Added DATA_PATH parameter support to the NEST AWS deployment script. This allows Maria to optionally pass a data path that will be available to the agent as the `DATA_PATH` environment variable.

## Changes Made

### 1. Added DATA_PATH Parameter (Line 21)
```bash
DATA_PATH="${12:-}"    # Optional data path
```

### 2. Updated Usage/Help Text (Lines 25, 28, 38-42)
- Added `[DATA_PATH]` to usage statement
- Added DATA_PATH example in example command
- Added DATA_PATH parameter description

### 3. Added DATA_PATH to Deployment Output (Line 54)
```bash
echo "Data Path: ${DATA_PATH:-"None (no data attached)"}"
```

### 4. Added DATA_PATH Logging in User-Data Script (Lines 169-174)
```bash
# Log data path status
if [ -n "$DATA_PATH" ]; then
    echo "DATA_PATH is set to: $DATA_PATH"
else
    echo "No DATA_PATH provided; starting agent without attached data."
fi
```

### 5. Exported DATA_PATH Environment Variable (Line 191)
```bash
export DATA_PATH='$DATA_PATH'
```

## Updated Defaults
- `REGISTRY_URL` default changed to: `http://registry.chat39.com:6900`
- `INSTANCE_TYPE` default changed to: `t3.small`

## Testing

### Quick Syntax Check
```bash
bash -n scripts/aws-single-agent-deployment.sh
```

### Simulate Script Call (No AWS)
```bash
# Test with DATA_PATH
bash scripts/aws-single-agent-deployment.sh \
  "test-agent" \
  "sk-ant-test" \
  "Test Agent" \
  "testing" \
  "test specialist" \
  "Test description" \
  "testing" \
  "" \
  "6000" \
  "us-east-1" \
  "t3.small" \
  "/data/hr.csv"

# Test without DATA_PATH (should work with empty 12th arg)
bash scripts/aws-single-agent-deployment.sh \
  "test-agent" \
  "sk-ant-test" \
  "Test Agent" \
  "testing" \
  "test specialist" \
  "Test description" \
  "testing"
```

### Verify User-Data Script Generation
After running the script (even with invalid AWS credentials), check the generated `user_data_${AGENT_ID}.sh` file:
- Should contain `export DATA_PATH='...'` line
- Should contain the logging section for DATA_PATH

## Next Steps
- Agent code (`examples/nanda_agent.py`) can now read `DATA_PATH` from environment
- Data loading logic can be added to agent initialization
- MCP tools can be registered to access the data

