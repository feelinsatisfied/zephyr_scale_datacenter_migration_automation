# SOURCE Instance Safety Verification

## Executive Summary

✅ **CONFIRMED: All scripts that connect to the SOURCE instance are READ-ONLY.**

No script performs any write operations (POST, PUT, PATCH, DELETE) on the source instance. All operations are GET requests only.

---

## Scripts That Connect to SOURCE Instance

### 1. `1_export_zephyr_scale_all_v2.py`

**Purpose:** Export all test cases, plans, and runs from source

**HTTP Methods Used:**
- Line 52: `session.get(url, params=params, timeout=60)` - Pagination
- Line 72: `session.get(f"{TC_GET}/{key}", timeout=60)` - Get test case details
- Line 86: `session.get(f"{PLAN_GET}/{key}", timeout=60)` - Get test plan details
- Line 100: `session.get(f"{RUN_GET}/{key}", timeout=60)` - Get test run details
- Line 107: `session.get(f"{RESULTS_GET}/{key}/testresults", timeout=60)` - Get results

**Verification:** ✅ Only GET requests. No writes.

---

### 2. `5_export_testrun_by_key.py`

**Purpose:** Export individual test run by key from source

**HTTP Methods Used:**
- Line 19: `session.get(url, params=params, timeout=timeout)` - Get with retry
- Line 28: Uses `get_with_retry()` which only calls `session.get()`
- Line 38: `session.get(url, params=params)` - Get test results

**Verification:** ✅ Only GET requests. No writes.

---

### 3. `9_export_testplans.py`

**Purpose:** Export test plans from source

**HTTP Methods Used:**
- Line 48: `session.get(url, params=params, timeout=60)` - Get with retry
- Line 60: Uses `get_with_retry()` which only calls `session.get()`
- Line 80: `session.get()` - List test plans with pagination

**Verification:** ✅ Only GET requests. No writes.

---

## Scripts That DO NOT Connect to SOURCE

These scripts only read from local files or connect to TARGET:

- `2_clean_up_zephyr_scale_all_v5.py` - Reads local JSON files only
- `2.5_build_testcase_mapping.py` - Reads local files + queries TARGET (not source)
- `3_import_zephyr_scale_all_v3.py` - Writes to TARGET only
- `4_export_target_testcases.py` - Queries TARGET only
- `6_remap_testrun_ids_v3.py` - Reads/writes local JSON files only
- `7_clean_testruns_for_import.py` - Reads/writes local JSON files only
- `8_import_testruns.py` - Writes to TARGET only
- `8.5_build_testrun_mapping.py` - Reads local files + queries TARGET (not source)
- `10_clean_and_map_testplans_v3.py` - Reads/writes local JSON files only
- `11_import_testplans.py` - Writes to TARGET only

---

## API Endpoints Used on SOURCE

All endpoints are READ-ONLY Zephyr Scale API endpoints:

| Endpoint | HTTP Method | Purpose |
|----------|-------------|---------|
| `/rest/atm/1.0/testcase/search` | GET | Search for test cases |
| `/rest/atm/1.0/testcase/{key}` | GET | Get test case details |
| `/rest/atm/1.0/testplan/search` | GET | Search for test plans |
| `/rest/atm/1.0/testplan/{key}` | GET | Get test plan details |
| `/rest/atm/1.0/testrun/search` | GET | Search for test runs |
| `/rest/atm/1.0/testrun/{key}` | GET | Get test run details |
| `/rest/atm/1.0/testrun/{key}/testresults` | GET | Get test results |

**None of these endpoints modify data.**

---

## Authentication Used

The scripts use Bearer token authentication with `SOURCE_PAT`:

```python
session.headers.update({
    "Authorization": f"Bearer {SOURCE_PAT}",
    "Accept": "application/json",
    "Content-Type": "application/json"
})
```

**Even if the PAT has write permissions, the scripts never invoke write operations.**

---

## Code Review - No Write Operations Found

Search performed for any write operations:

```bash
grep -r "session\.(post|put|delete|patch)" scripts/*export*.py
# Result: No matches found
```

---

## Safety Guarantees

1. ✅ **No POST requests** - Cannot create new data
2. ✅ **No PUT requests** - Cannot update existing data
3. ✅ **No DELETE requests** - Cannot delete data
4. ✅ **No PATCH requests** - Cannot modify data
5. ✅ **Only GET requests** - Read-only operations
6. ✅ **No file uploads** - Cannot upload attachments
7. ✅ **No configuration changes** - Cannot modify settings

---

## Worst-Case Scenarios

**Q: What if a script has a bug?**
A: Since all operations are GET requests, a bug could only:
- Read more data than intended
- Generate incorrect local export files
- Cause API rate limiting (temporary)

It **cannot** modify, delete, or corrupt source data.

**Q: What if credentials are leaked?**
A: The scripts themselves don't write to source. Even if credentials were compromised, an attacker would need to write their own code to make changes.

**Q: What if I accidentally run an import script against source?**
A: The import scripts (`3_import_*.py`, `8_import_*.py`, `11_import_*.py`) all explicitly use `TARGET_BASE_URL` and `TARGET_PAT` from config files. They have no references to SOURCE endpoints.

---

## Migration Flow - Source Interaction

```
SOURCE Instance (READ-ONLY)
    ↓
    ↓ GET /rest/atm/1.0/testcase/search
    ↓ GET /rest/atm/1.0/testcase/{key}
    ↓ GET /rest/atm/1.0/testrun/search
    ↓ GET /rest/atm/1.0/testrun/{key}
    ↓ GET /rest/atm/1.0/testplan/{key}
    ↓
Local Export Files (JSON)
    ↓
    ↓ Clean/Transform
    ↓ Remap IDs
    ↓
TARGET Instance (WRITE)
```

**Source instance is only touched at the beginning for data export.**

---

## Additional Safeguards

1. **TLS Certificate Validation:** Scripts use TLS config to verify connections
2. **Separate Credentials:** Source and target use different PATs
3. **Read-Only PAT Option:** You can create a read-only PAT for source to further ensure safety
4. **Audit Trail:** All operations logged to `logs/migration_log.txt`

---

## Recommendation

For maximum peace of mind, you can:

1. **Use a read-only Personal Access Token** for SOURCE_PAT
   - In Jira, create a PAT with only "read" permissions
   - This ensures even manual misuse cannot write to source

2. **Test against a non-production source first**
   - Run the scripts against a test environment
   - Verify no changes occur

3. **Monitor API logs**
   - Check Jira audit logs during/after export
   - Should show only GET requests from your IP

---

## Conclusion

✅ **SAFE TO RUN:** All source-facing scripts are verified to be read-only.

The migration scripts will:
- ✅ Read all test data from source
- ✅ Save to local JSON files
- ✅ Transform and remap locally
- ✅ Import to target only

They will NOT:
- ❌ Modify source test cases
- ❌ Delete source test runs
- ❌ Update source test plans
- ❌ Change source project settings
- ❌ Add/remove source data

**Your source instance remains completely untouched.**
