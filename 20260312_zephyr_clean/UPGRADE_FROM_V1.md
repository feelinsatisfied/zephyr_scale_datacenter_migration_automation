# Upgrading from Your Current Migration Scripts

## What Was Wrong With the Old Approach?

Your current script `6_remap_testrun_ids.py:47-50` tries to find `oldKey` or `legacyKey` in the target test case export:

```python
def load_mapping(target_dir):
    for case in data.get("values", []):
        old_key = case.get("oldKey") or case.get("legacyKey")  # ← THESE DON'T EXIST!
        new_key = case.get("key")
        if old_key and new_key:
            mapping[old_key] = new_key
```

**Problem:** After importing test cases to the target, Zephyr Scale doesn't automatically store a reference to the source key. The target export only has the NEW keys, so `oldKey` is always `None`, and the mapping is empty!

## What Changed in V2?

### The Fix

Instead of looking for non-existent `oldKey` fields, we now:

1. **Match test cases by content** (name + description + steps) after import
2. **Build the mapping** by correlating source and target entities
3. **Use the mapping** to update references before importing dependent data

### Files Added

| File | Purpose |
|------|---------|
| `scripts/2.5_build_testcase_mapping.py` | Builds source→target test case key mapping AFTER import |
| `scripts/8.5_build_testrun_mapping.py` | Builds source→target test run key mapping AFTER import |
| `0_run_zephyr_migration_orchestrator_v2.py` | Updated orchestrator with mapping steps |

### Files Updated

| File | What Changed |
|------|--------------|
| `scripts/6_remap_testrun_ids_v3.py` | Now reads `testcase_key_mapping.json` instead of looking for `oldKey` |
| `scripts/10_clean_and_map_testplans_v3.py` | Now uses BOTH mapping files (test cases AND test runs) |

## How to Upgrade

### Option 1: Fresh Start (Recommended)

If your target instance is empty or you can clear it:

1. **Backup your current scripts** (just in case):
   ```bash
   cd ~/Desktop/Zephyr
   cp -r scripts scripts_backup_$(date +%Y%m%d)
   ```

2. **Copy the new/updated scripts** - The new scripts are already in your `scripts/` directory:
   - `2.5_build_testcase_mapping.py` (NEW)
   - `8.5_build_testrun_mapping.py` (NEW)
   - `6_remap_testrun_ids_v3.py` (UPDATED)
   - `10_clean_and_map_testplans_v3.py` (UPDATED)

3. **Use the new orchestrator**:
   ```bash
   python 0_run_zephyr_migration_orchestrator_v2.py
   ```

### Option 2: Resume Partially Completed Migration

If you've already imported test cases to the target:

1. **Build the test case mapping NOW**:
   ```bash
   cd ~/Desktop/Zephyr/scripts
   python 2.5_build_testcase_mapping.py
   ```

   This will:
   - Fetch all test cases from your TARGET instance
   - Match them to source test cases
   - Create `exports/testcase_key_mapping.json`

2. **Continue with test runs** using the new scripts:
   ```bash
   python 6_remap_testrun_ids_v3.py  # Now uses the mapping you just built
   python 7_clean_testruns_for_import.py
   python 8_import_testruns.py
   python 8.5_build_testrun_mapping.py  # Build run mapping
   ```

3. **Finish with test plans**:
   ```bash
   python 9_export_testplans.py
   python 10_clean_and_map_testplans_v3.py  # Uses both mappings
   python 11_import_testplans.py
   ```

## Verification

After upgrading, verify the mappings were built correctly:

```bash
# Check test case mapping
cat ~/Desktop/zephyr/exports/testcase_key_mapping.json | head -20

# Should show entries like:
# {
#   "SOURCE-T123": "TARGET-T456",
#   "SOURCE-T124": "TARGET-T457",
#   ...
# }

# Check test run mapping (after step 8.5)
cat ~/Desktop/zephyr/exports/testrun_key_mapping.json | head -20
```

## What to Expect

### Successful Mapping Output

When you run `2.5_build_testcase_mapping.py`, you should see:

```
🔗 Building Test Case Key Mapping (Source → Target)
📖 Loading source test cases from .../testcases_source.json
📊 Loaded 150 source test cases
📥 Fetching test cases from TARGET (YOURPROJECT)...
  Retrieved 150 test cases so far...
✅ Retrieved 150 test cases from TARGET
🔨 Building source→target mapping...
✅ Mapped 150 test cases
💾 Saved mapping to .../testcase_key_mapping.json
📈 Coverage: 150/150 test cases mapped (100%)
✅ Mapping complete!
```

### Warning Signs

If you see low coverage:

```
⚠️ WARNING: 50 source test cases could not be matched:
  - SOURCE-T100
  - SOURCE-T101
  ...
📈 Coverage: 100/150 test cases mapped (66%)
```

**This means:**
- Some test cases failed to import
- Some test case names/content changed between export and import
- There may be duplicate test cases

**Action:** Review the unmapped keys and investigate why they don't match.

## Key Differences Summary

| Aspect | Old Approach (Broken) | New Approach (Working) |
|--------|----------------------|----------------------|
| **When mapping is built** | Before import (impossible!) | After import ✅ |
| **How mapping is built** | Looks for `oldKey` field | Matches by content ✅ |
| **What gets mapped** | Nothing (field doesn't exist) | All test cases/runs ✅ |
| **Result** | Broken links ❌ | Preserved links ✅ |

## Need Help?

If something doesn't work:

1. Check `logs/migration_log.txt` for detailed error messages
2. Verify the mapping files were created and have content
3. Review the MIGRATION_GUIDE.md for troubleshooting steps

## Quick Command Reference

```bash
# Clean slate migration
cd ~/Desktop/Zephyr
python 0_run_zephyr_migration_orchestrator_v2.py

# Build test case mapping only (if already imported)
cd ~/Desktop/Zephyr/scripts
python 2.5_build_testcase_mapping.py

# Check mapping coverage
grep "Coverage:" ~/Desktop/zephyr/logs/migration_log.txt

# View mapping file
cat ~/Desktop/zephyr/exports/testcase_key_mapping.json

# Resume from a specific step
cd ~/Desktop/Zephyr/scripts
python 6_remap_testrun_ids_v3.py  # Or any other step
```

---

**Bottom Line:** The new approach fixes the core issue by building mappings AFTER import using intelligent content matching, which actually works! 🎉