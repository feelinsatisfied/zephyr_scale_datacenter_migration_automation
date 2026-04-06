# Zephyr Scale Data Center Migration Guide

## Overview

This toolset migrates **all Zephyr Scale test data** from one Jira Data Center instance to another **while preserving all relationships and links** between test cases, test runs/cycles, and test plans.

### The Core Challenge

When you export data from the source instance and import it to the target instance, Zephyr Scale assigns **new IDs and keys** to everything. This breaks all the relationships:

- Test runs reference test cases by key (e.g., `PROJ-T123`)
- Test plans reference both test cases and test runs by key
- After import, `PROJ-T123` becomes `TARGET-T456`, breaking all links

### The Solution

The enhanced migration process builds **ID mapping files** after each import phase by matching entities based on their immutable attributes (name, description, steps, etc.). These mappings are then used to update references in subsequent data types.

## Migration Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    PHASE 1: TEST CASES                      │
├─────────────────────────────────────────────────────────────┤
│ 1. Export from SOURCE    →  testcases_source.json          │
│ 2. Clean data            →  testcases_source_clean.json    │
│ 3. Import to TARGET      →  Creates new test cases         │
│ 2.5. BUILD MAPPING       →  testcase_key_mapping.json      │
│                              { "SRC-T1": "TGT-T1", ... }    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    PHASE 2: TEST RUNS                       │
├─────────────────────────────────────────────────────────────┤
│ 5. Export from SOURCE    →  testruns_source/*.json         │
│ 6. REMAP test case keys  →  testruns_remapped/*.json       │
│    (uses testcase_key_mapping.json)                         │
│ 7. Clean data            →  testruns_clean/*.json          │
│ 8. Import to TARGET      →  Creates new test runs          │
│ 8.5. BUILD MAPPING       →  testrun_key_mapping.json       │
│                              { "SRC-R1": "TGT-R1", ... }    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    PHASE 3: TEST PLANS                      │
├─────────────────────────────────────────────────────────────┤
│ 9. Export from SOURCE    →  testplans_source/*.json        │
│ 10. REMAP all keys       →  testplans_clean/*.json         │
│     (uses both mapping files)                               │
│ 11. Import to TARGET     →  Creates new test plans         │
└─────────────────────────────────────────────────────────────┘
```

## What's New in v2?

### New Scripts

1. **2.5_build_testcase_mapping.py**
   - Runs AFTER test case import (step 3)
   - Fetches all test cases from TARGET via API
   - Matches them to source test cases using signatures (name + description + steps)
   - Outputs: `testcase_key_mapping.json`

2. **8.5_build_testrun_mapping.py**
   - Runs AFTER test run import (step 8)
   - Fetches all test runs from TARGET via API
   - Matches them to source runs using signatures (name + description + item count)
   - Outputs: `testrun_key_mapping.json`

### Updated Scripts

1. **6_remap_testrun_ids_v3.py**
   - Now uses `testcase_key_mapping.json` (not the broken approach from v2)
   - Recursively finds all `testCaseKey` references and remaps them
   - Removes unmapped references to prevent import errors

2. **10_clean_and_map_testplans_v3.py**
   - Uses BOTH mapping files:
     - `testcase_key_mapping.json` for test case references
     - `testrun_key_mapping.json` for test run references
   - Remaps all linked entities before import

3. **0_run_zephyr_migration_orchestrator_v2.py**
   - Integrated all new mapping steps
   - Enhanced logging and progress tracking
   - Clear phase separation

## Directory Structure

```
~/Desktop/zephyr/
├── 0_run_zephyr_migration_orchestrator_v2.py  ← Run this!
├── config/
│   ├── source_base_url.txt
│   ├── source_pat.txt
│   ├── source_proj_key.txt
│   ├── target_base_url.txt
│   ├── target_pat.txt
│   └── target_proj_key.txt
├── certs/
│   ├── aws_cert_dev.crt
│   ├── zephyr_cert_test.crt
│   └── zephyr_pw_key.key
├── scripts/
│   ├── config_loader.py
│   ├── 1_export_zephyr_scale_all_v2.py
│   ├── 2_clean_up_zephyr_scale_all_v5.py
│   ├── 2.5_build_testcase_mapping.py           ← NEW
│   ├── 3_import_zephyr_scale_all_v3.py
│   ├── 5_export_testrun_by_key.py
│   ├── 6_remap_testrun_ids_v3.py               ← UPDATED
│   ├── 7_clean_testruns_for_import.py
│   ├── 8_import_testruns.py
│   ├── 8.5_build_testrun_mapping.py            ← NEW
│   ├── 9_export_testplans.py
│   ├── 10_clean_and_map_testplans_v3.py        ← UPDATED
│   └── 11_import_testplans.py
├── exports/
│   ├── testcases_source/
│   ├── testcase_key_mapping.json               ← GENERATED
│   ├── testruns_source/
│   ├── testruns_remapped/
│   ├── testrun_key_mapping.json                ← GENERATED
│   ├── testplans_source/
│   └── testplans_clean/
└── logs/
    └── migration_log.txt
```

## How to Run

### Prerequisites

1. **Configuration Files**: All config/*.txt files must be populated
2. **Certificates**: All certs/*.crt and *.key files must be present
3. **Python**: Python 3.6+ with `requests` library installed
4. **Permissions**: Source and target PATs must have Zephyr Scale admin permissions

### Running the Migration

```bash
cd ~/Desktop/zephyr
python 0_run_zephyr_migration_orchestrator_v2.py
```

The orchestrator will:
1. Run all steps in sequence
2. Skip steps that have already completed (based on output file existence)
3. Stop if any step fails
4. Log everything to `logs/migration_log.txt`

### Re-running After Errors

If a step fails:
1. Review the error in `logs/migration_log.txt`
2. Fix the issue (permissions, API limits, data problems, etc.)
3. Re-run the orchestrator - it will skip completed steps and resume

### Manual Step Execution

You can also run individual steps manually:

```bash
cd ~/Desktop/zephyr/scripts
python 2.5_build_testcase_mapping.py
```

## How the Mapping Works

### Test Case Matching Algorithm

```python
def build_testcase_signature(tc):
    name = normalize_text(tc.get("name"))
    description = normalize_text(tc.get("description"))
    steps = first_2_steps_from_test_script(tc)
    return f"{name}||{description}||{steps}"
```

**Why this works:**
- Test case names are typically unique within a project
- Description + first few steps provide additional uniqueness
- These fields don't change during export/import

**Potential Issues:**
- Duplicate test case names → First match is used, logged as warning
- Modified test cases between export/import → Won't match
- Very similar test cases → May match incorrectly

### Test Run Matching Algorithm

```python
def build_testrun_signature(run):
    name = normalize_text(run.get("name"))
    description = normalize_text(run.get("description"))
    environment = normalize_text(run.get("environment"))
    version = normalize_text(run.get("version"))
    item_count = len(run.get("items", []))
    return f"{name}||{description}||env:{environment}||ver:{version}||items:{item_count}"
```

**Why this works:**
- Test run names + metadata are typically unique
- Item count provides additional verification
- These fields are preserved during migration

## Troubleshooting

### Issue: Low mapping coverage (< 90%)

**Possible Causes:**
1. Test cases were modified between export and import
2. Source data contains duplicates
3. Some test cases failed to import

**Solutions:**
1. Check `logs/migration_log.txt` for import errors
2. Review unmapped keys listed in mapping script output
3. Manually verify a few unmapped cases in both instances
4. Consider re-running the import if many cases failed

### Issue: Test runs still not linked after import

**Possible Causes:**
1. Test case mapping wasn't built (step 2.5 skipped/failed)
2. Test runs reference test cases that weren't imported
3. Test run remapping failed

**Solutions:**
1. Verify `exports/testcase_key_mapping.json` exists and has entries
2. Check `logs/migration_log.txt` for step 6 warnings about unmapped keys
3. Manually inspect a remapped test run JSON to verify keys were updated

### Issue: Mapping file shows unexpected matches

**Symptoms:**
- Source test case `PROJ-T100` mapped to wrong target case
- Multiple source cases mapped to same target case

**Solutions:**
1. The signature-matching algorithm may need tuning for your data
2. Consider adding more fields to the signature (labels, priority, etc.)
3. Manually review and edit the mapping JSON file before running step 6

## Advanced Customization

### Adjusting the Matching Algorithm

Edit `scripts/2.5_build_testcase_mapping.py` line 41-56 to customize the signature:

```python
def build_testcase_signature(tc):
    # Add more fields for uniqueness
    name = normalize_text(tc.get("name", ""))
    priority = tc.get("priority", "")
    labels = sorted(tc.get("labels", []))

    return f"{name}||{priority}||{labels}"
```

### Handling Large Datasets

For projects with 10,000+ test cases:

1. **Increase pagination size** in `2.5_build_testcase_mapping.py` line 74:
   ```python
   page_size = 500  # Default is 200
   ```

2. **Add progress tracking** for long-running operations

3. **Consider splitting by folder** - migrate one folder at a time

### Pre-Migration Validation

Before running the migration, validate your data:

```bash
# Count test cases in source
curl -H "Authorization: Bearer $SOURCE_PAT" \
  "$SOURCE_BASE_URL/rest/atm/1.0/testcase/search?query=projectKey=\"$PROJECT\""

# Count test cases in target (should be 0 before migration)
curl -H "Authorization: Bearer $TARGET_PAT" \
  "$TARGET_BASE_URL/rest/atm/1.0/testcase/search?query=projectKey=\"$PROJECT\""
```

## Verifying Success

After migration completion:

1. **Check mapping coverage:**
   ```bash
   # Should show high percentages (>90%)
   grep "Coverage:" logs/migration_log.txt
   ```

2. **Verify test run links:**
   - Open a test run in target Jira
   - Confirm it shows test cases (not broken references)
   - Check execution history is preserved

3. **Verify test plan links:**
   - Open a test plan in target Jira
   - Confirm it lists test cases and test runs
   - All links should be active (clickable)

4. **Spot-check data integrity:**
   - Compare a complex test case in source vs target
   - Verify steps, attachments, custom fields
   - Check test run execution results

## Known Limitations

1. **Attachments**: Not migrated (Zephyr API limitation)
2. **Comments**: Not migrated (removed during clean)
3. **Custom Fields**: Only migrated if field exists in target project
4. **User References**: May break if users don't exist in target instance
5. **Execution History**: Timestamps may not be preserved
6. **Folders**: Created as needed, but hierarchy may differ slightly

## Getting Help

If you encounter issues:

1. **Check the logs**: `logs/migration_log.txt` has detailed output
2. **Review generated files**: Inspect the JSON outputs for anomalies
3. **Validate mappings**: Open and review the mapping JSON files
4. **Test with a small dataset**: Try migrating a single test case manually first

## Migration Checklist

- [ ] All config files populated
- [ ] All certificates in place
- [ ] Source and target instances accessible
- [ ] PATs have correct permissions
- [ ] Target project exists and is empty
- [ ] Backup of source data taken
- [ ] Orchestrator executed successfully
- [ ] Mapping files generated with good coverage
- [ ] Spot checks of data completed
- [ ] All test cases visible in target
- [ ] Test runs show linked test cases
- [ ] Test plans show linked runs and cases
- [ ] Custom fields migrated correctly

## Summary

This enhanced migration toolkit solves the ID remapping problem by:

1. ✅ Importing entities in the correct order (cases → runs → plans)
2. ✅ Building mappings AFTER import by matching on immutable attributes
3. ✅ Using mappings to update references in subsequent imports
4. ✅ Preserving all relationships between test entities
5. ✅ Providing detailed logging and validation

The result: **Complete Zephyr Scale project migration with all links intact!**