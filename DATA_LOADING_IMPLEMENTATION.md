# Data Loading Implementation - Step 3

## Summary
Modified `examples/nanda_agent.py` to read `DATA_PATH` from environment and load attached data (CSV and JSON support). The agent now loads data on startup and makes it available via `AGENT_CONFIG["data"]`.

## Changes Made

### 1. Added Pandas Import (Lines 28-34)
```python
# Try to import pandas for CSV support
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    print("⚠️ Warning: pandas library not available. CSV data loading will be disabled. Install with: pip install pandas")
```

### 2. Added DATA_PATH Environment Variable (Line 100)
```python
# Data path from environment
DATA_PATH = os.getenv("DATA_PATH", None)
```

### 3. Added load_attached_data() Function (Lines 106-145)
- Supports CSV files (requires pandas)
- Supports JSON files (built-in json module)
- Graceful error handling
- Informative logging

**Function signature:**
```python
def load_attached_data(path):
    """
    Load data from a file path. Supports CSV and JSON formats.
    
    Args:
        path: File path to load data from
        
    Returns:
        Loaded data (DataFrame for CSV, dict/list for JSON) or None if failed
    """
```

**Features:**
- CSV: Returns pandas DataFrame, logs shape
- JSON: Returns dict/list, logs keys or item count
- Error handling: FileNotFoundError, general exceptions
- Format validation: Only .csv and .json supported

### 4. Updated main() Function (Lines 245-257)
Added data loading logic:
```python
# Load attached data if DATA_PATH is provided
attached_data = None
if DATA_PATH:
    print(f"📂 Loading data from: {DATA_PATH}")
    attached_data = load_attached_data(DATA_PATH)
    if attached_data is not None:
        if PANDAS_AVAILABLE and isinstance(attached_data, pd.DataFrame):
            print(f"📊 Loaded data with shape: {attached_data.shape}")
        AGENT_CONFIG["data"] = attached_data
    else:
        print("⚠️ Data loading failed, continuing without attached data")
else:
    print("ℹ️ No DATA_PATH provided; starting agent without attached data")
```

### 5. Updated setup.py
Added `pandas` to requirements (line 21):
```python
"pandas"   # For CSV data loading
```

### 6. Created Sample Test Data
Created `tests/sample_hr.csv` with sample HR data for testing.

## Data Access

After loading, data is available in:
- `AGENT_CONFIG["data"]` - Contains the loaded DataFrame (CSV) or dict/list (JSON)
- Can be accessed in agent logic functions via the config parameter

## Testing

### Test Without Data
```bash
python examples/nanda_agent.py
```
Expected output:
```
ℹ️ No DATA_PATH provided; starting agent without attached data
```

### Test With CSV Data
```bash
# Windows PowerShell
$env:DATA_PATH="tests/sample_hr.csv"; python examples/nanda_agent.py

# Linux/Mac
DATA_PATH=tests/sample_hr.csv python examples/nanda_agent.py
```
Expected output:
```
📂 Loading data from: tests/sample_hr.csv
✅ Loaded CSV data with shape: (10, 5)
📊 Loaded data with shape: (10, 5)
```

### Test With JSON Data
```bash
# Create a sample JSON file first
echo '{"key": "value", "numbers": [1, 2, 3]}' > tests/sample.json

# Then run
DATA_PATH=tests/sample.json python examples/nanda_agent.py
```
Expected output:
```
📂 Loading data from: tests/sample.json
✅ Loaded JSON data
   Keys: ['key', 'numbers']
```

### Test With Invalid Path
```bash
DATA_PATH=/nonexistent/file.csv python examples/nanda_agent.py
```
Expected output:
```
📂 Loading data from: /nonexistent/file.csv
❌ Failed to load data: File not found at /nonexistent/file.csv
⚠️ Data loading failed, continuing without attached data
```

## Next Steps (Step 4 - Tomorrow)

After data loads correctly, expose it via MCP tools:
- Create MCP tool: `get_row_count`
- Description: returns number of rows in attached dataset
- Input: none
- Output: integer

## Files Modified

1. `NEST/examples/nanda_agent.py` - Added data loading functionality
2. `NEST/setup.py` - Added pandas to requirements
3. `NEST/tests/sample_hr.csv` - Created sample test data

## Verification Checklist

- ✅ DATA_PATH read from environment
- ✅ CSV loading with pandas support
- ✅ JSON loading with built-in json
- ✅ Error handling for missing files
- ✅ Error handling for unsupported formats
- ✅ Logging for data loading status
- ✅ Data added to AGENT_CONFIG["data"]
- ✅ Agent starts normally without data
- ✅ Agent starts normally with data
- ✅ Sample test data created

