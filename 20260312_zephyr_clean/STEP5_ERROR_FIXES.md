# Step 5 Error - Fixes Applied

## Errors Encountered

### Error 1: Step 2.5 - File Not Found
```
Source test cases file not found: ~/Desktop/zephyr/exports/testcases_source/testcases_source.json
```

### Error 2: Step 5 - Missing Required Argument
```
5_export_testrun_by_key.py: error: the following arguments are required: --run-key
```

---

## Root Causes

### Issue 1: Case Sensitivity Mismatch
- **Scripts expected:** `~/Desktop/zephyr` (lowercase)
- **Actual directory:** `~/Desktop/Zephyr` (capital Z)
- **Impact:** Scripts couldn't find config, exports, etc.

### Issue 2: File Path Mismatch
- **Step 1 outputs to:** `exports/zephyr_scale_full_export.json`
- **Step 2.5 expected:** `exports/testcases_source/testcases_source.json`
- **Impact:** Step 2.5 couldn't find source test cases

### Issue 3: Wrong Script for Step 5
- **Current script:** `5_export_testrun_by_key.py` (exports ONE test run by key)
- **Needed:** Bulk export of ALL test runs
- **Impact:** Step 5 failed with missing `--run-key` argument

---

## Fixes Applied

### ✅ Fix 1: Updated config_loader.py
**File:** `scripts/config_loader.py`
**Change:** Line 13
```python
# BEFORE
BASE_PATH = os.path.expanduser("~/Desktop/zephyr")

# AFTER
BASE_PATH = os.path.expanduser("~/Desktop/Zephyr")  # Capital Z
```

### ✅ Fix 2: Updated 2.5_build_testcase_mapping.py
**File:** `scripts/2.5_build_testcase_mapping.py`
**Change:** Line 33
```python
# BEFORE
SOURCE_CASES_FILE = os.path.join(EXPORT_DIR, "testcases_source", "testcases_source.json")

# AFTER
SOURCE_CASES_FILE = os.path.join(EXPORT_DIR, "zephyr_scale_full_export.json")
```
**Why:** Matches the actual output from step 1

### ✅ Fix 3: Created New Step 5 Script
**File:** `scripts/5_export_testruns_from_full_export.py` (NEW)
**Purpose:** Extracts test runs from the full export created in step 1
**Replaces:** `5_export_testrun_by_key.py` (which is for individual exports)

**What it does:**
1. Reads `exports/zephyr_scale_full_export.json`
2. Extracts the `testRuns` array
3. Saves each test run as a separate file in `exports/testruns_source/`
4. Format: `{RUN_KEY}.json` (e.g., `PROJ-R123.json`)

### ✅ Fix 4: Updated Orchestrator v2
**File:** `0_run_zephyr_migration_orchestrator_v2.py`
**Changes:**
1. Line 14: Changed `ROOT = DESKTOP / "zephyr"` to `ROOT = DESKTOP / "Zephyr"`
2. Line 26: Changed step 5 script name to `"5_export_testruns_from_full_export.py"`

---

## Files Modified

| File | Type | What Changed |
|------|------|--------------|
| `scripts/config_loader.py` | Modified | Fixed base path (lowercase → Zephyr) |
| `scripts/2.5_build_testcase_mapping.py` | Modified | Fixed source file path |
| `scripts/5_export_testruns_from_full_export.py` | **NEW** | Extracts test runs from full export |
| `0_run_zephyr_migration_orchestrator_v2.py` | Modified | Fixed ROOT path + step 5 script name |

---

## Testing the Fixes

### Verify Paths are Correct
```bash
cd ~/Desktop/Zephyr
python scripts/config_loader.py
```

**Expected output:**
```
🌐 Loaded config:
  SOURCE_BASE_URL = https://your-source-jira.com
  SOURCE_PROJECT_KEY = YOUR_SOURCE_PROJECT
  TARGET_BASE_URL = https://your-target-jira.com
  TARGET_PROJECT_KEY = YOUR_TARGET_PROJECT
  Certs loaded: True, True, True
```

### Run Step 2.5 Manually
```bash
cd ~/Desktop/Zephyr
python scripts/2.5_build_testcase_mapping.py
```

**Expected:**
- Should find `exports/zephyr_scale_full_export.json`
- Should connect to TARGET and fetch test cases
- Should build mapping and save to `exports/testcase_key_mapping.json`

### Run Step 5 Manually
```bash
cd ~/Desktop/Zephyr
python scripts/5_export_testruns_from_full_export.py
```

**Expected:**
- Should read `exports/zephyr_scale_full_export.json`
- Should extract test runs to `exports/testruns_source/*.json`
- One file per test run

### Run Full Orchestrator
```bash
cd ~/Desktop/Zephyr
python 0_run_zephyr_migration_orchestrator_v2.py
```

**Expected:**
- Steps should run in sequence
- No more file not found errors
- No more missing argument errors

---

## What Happens Next

After these fixes, the migration flow is:

1. ✅ **Step 1:** Export all data from source → `zephyr_scale_full_export.json`
2. ✅ **Step 2:** Clean the export → `zephyr_scale_full_clean.json`
3. ✅ **Step 3:** Import test cases to target (with folders!)
4. ✅ **Step 2.5:** Build test case mapping → `testcase_key_mapping.json`
5. ✅ **Step 5:** Extract test runs → `testruns_source/*.json`
6. ✅ **Step 6:** Remap test run references → `testruns_remapped/*.json`
7. **Step 7:** Clean test runs
8. **Step 8:** Import test runs to target
9. **Step 8.5:** Build test run mapping → `testrun_key_mapping.json`
10. **Step 9:** Export test plans from source
11. **Step 10:** Remap test plan references (uses both mappings)
12. **Step 11:** Import test plans to target

---

## Summary

All three errors are now fixed:
- ✅ Path case sensitivity fixed (Zephyr with capital Z)
- ✅ Step 2.5 now finds source test cases
- ✅ Step 5 now extracts test runs without requiring arguments

The migration should now proceed smoothly from step 5 onwards!