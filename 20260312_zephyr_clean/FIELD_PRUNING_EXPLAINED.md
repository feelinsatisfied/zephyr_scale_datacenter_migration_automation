# Zephyr Scale Field Pruning Explained

## What is Field Pruning?

Field pruning is the process of **filtering out fields that shouldn't be sent** to the Zephyr Scale import API. This happens in two places:

1. **Step 2** - `2_clean_up_zephyr_scale_all_v5.py` - Removes forbidden/auto-generated fields
2. **Step 3** - `3_import_zephyr_scale_all_v3.py` - Keeps only API-accepted fields

## Why Do We Need Pruning?

### Problem Without Pruning

If you send the raw export data directly to the target instance, you'll get errors like:

```json
{
  "errorMessages": ["Field 'id' is not allowed during creation"],
  "errors": {
    "key": "Cannot set key during creation - it will be auto-generated",
    "createdOn": "Field is read-only"
  }
}
```

### Two-Stage Cleaning Approach

```
┌─────────────────────────────────────────────────────────┐
│  STEP 2: Remove Forbidden Fields (Cleaning)            │
├─────────────────────────────────────────────────────────┤
│  Removes:                                               │
│  • id, projectId, stepId                                │
│  • key (except in issueLinks context)                   │
│  • createdBy, createdOn, modifiedBy, modifiedOn         │
│  • updatedBy, updatedOn, executedBy, executionDate      │
│  • owner, comments, issueLinks                          │
│  • testRuns, testResults (nested objects)               │
│                                                         │
│  Why: These are auto-generated or context-specific      │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  STEP 3: Keep Only Allowed Fields (Pruning)            │
├─────────────────────────────────────────────────────────┤
│  Keeps ONLY:                                            │
│  • name, projectKey                                     │
│  • objective, precondition, priority                    │
│  • labels, componentNames                               │
│  • testScript, estimatedTime                            │
│  • customFields                                         │
│  • folder ← ADDED to preserve folder structure         │
│                                                         │
│  Why: These are the ONLY fields the Zephyr Scale        │
│       POST /testcase API accepts                        │
└─────────────────────────────────────────────────────────┘
```

## Fields Being Pruned in Step 3

### Test Cases

**Fields REMOVED (not in allowed list):**
- Any custom fields not in Zephyr's standard schema
- Source-specific metadata
- Any extra fields added by export process

**Fields KEPT (allowed list):**
```python
allowed_fields = [
    "name",              # Test case name (required)
    "projectKey",        # Target project (required)
    "objective",         # Test objective/purpose
    "precondition",      # Pre-conditions to run test
    "priority",          # Test priority (Low, Normal, High, etc.)
    "labels",            # Array of labels/tags
    "componentNames",    # Jira components
    "testScript",        # Test steps (required)
    "estimatedTime",     # Estimated execution time
    "customFields",      # Custom field values
    "folder"             # Folder path (e.g., "/Regression/Smoke Tests")
]
```

### Test Plans

Test plans are NOT pruned in the current script - they're passed as-is after cleaning in step 2.

### Test Runs

Test runs are NOT pruned - they're passed with their full structure (minus forbidden fields from step 2).

## Folder Field Behavior

### Before Fix (folder NOT in allowed_fields)

```python
# Source test case has folder
{
  "name": "Login Test",
  "folder": "/Regression/Authentication",
  "priority": "High",
  ...
}

# After pruning (folder removed!)
{
  "name": "Login Test",
  "priority": "High",
  ...
}

# Result: Test case imported to root folder ❌
```

### After Fix (folder in allowed_fields)

```python
# Source test case has folder
{
  "name": "Login Test",
  "folder": "/Regression/Authentication",
  "priority": "High",
  ...
}

# After pruning (folder preserved!)
{
  "name": "Login Test",
  "folder": "/Regression/Authentication",
  "priority": "High",
  ...
}

# Result: Test case imported to correct folder ✅
```

## How Folder Nesting Works

When you include the `"folder"` field in the import payload:

1. **Zephyr checks if folder exists** in target project
2. **If folder exists** → Test case is nested inside it
3. **If folder doesn't exist** → Import fails with error

### Current Script Behavior

The script has folder creation logic (lines 41-89 in `3_import_zephyr_scale_all_v3.py`), but it's only used for **test runs**, not test cases.

**For test cases:** You must manually create the folder structure in the target BEFORE import, OR the folders must already exist from previous imports.

## Can We Avoid Pruning?

**Short Answer:** No, you should NOT skip pruning entirely.

**Why:**
- Zephyr Scale API validates incoming fields strictly
- Unknown fields cause `400 Bad Request` errors
- Auto-generated fields (id, key) cause conflicts
- Read-only fields (createdOn, modifiedOn) are rejected

**What You CAN Do:**

1. **Add fields to allowed_fields** if they're valid Zephyr Scale API fields
2. **Remove fields from FORBIDDEN_FIELDS** in step 2 if they're actually allowed
3. **Consult Zephyr Scale API docs** to verify field names

### Example: Adding a Custom Field

If you have a custom field called `"testType"`:

```python
allowed_fields = [
    "name", "projectKey", "objective", "precondition", "priority",
    "labels", "componentNames", "testScript", "estimatedTime", "customFields",
    "folder",
    "testType"  # Add your custom field here
]
```

**Important:** The field must be:
1. Accepted by Zephyr Scale POST /testcase API
2. Configured in your target project
3. Have the same name/type as in source

## Pruned Fields That Might Matter

### Fields You Might Want Back

| Field | Why It's Removed | Can We Keep It? |
|-------|------------------|-----------------|
| `description` | Not in original allowed_fields | **YES** - Add to allowed_fields if Zephyr accepts it |
| `status` | Usually auto-set | **MAYBE** - Check if API allows setting status |
| `assignedTo` | User reference | **MAYBE** - If users exist in target |
| `environment` | Zephyr configuration | **MAYBE** - If environment exists in target |

### Fields You Should NOT Keep

| Field | Why It's Removed | Can We Keep It? |
|-------|------------------|-----------------|
| `id` | Auto-generated | **NO** - Will cause errors |
| `key` | Auto-generated | **NO** - Assigned by Zephyr |
| `createdOn` | Read-only timestamp | **NO** - Cannot be set |
| `createdBy` | Auto-set to current user | **NO** - Read-only |

## Testing Folder Import

To verify folders are working:

1. **Check your clean export** has folder fields:
   ```bash
   grep -i "folder" ~/Desktop/zephyr/exports/zephyr_scale_full_clean.json | head -5
   ```

2. **Verify folders exist in target** before import

3. **Run import** and check for folder-related errors

4. **Verify in Jira** that test cases appear in correct folders

## Recommendations

✅ **Do This:**
- Keep the two-stage cleaning (step 2) and pruning (step 3) process
- Add `"folder"` to allowed_fields (already done!)
- Add other valid fields as needed based on API docs
- Test with a small dataset first

❌ **Don't Do This:**
- Remove pruning entirely - will cause API errors
- Add auto-generated fields (id, key) to allowed_fields
- Add fields that don't exist in target project configuration

## Summary

**Pruning is necessary** to ensure import succeeds, but it can be **customized** to include additional valid fields like `folder`.

**The fix applied:**
```python
# BEFORE
allowed_fields = ["name", "projectKey", ..., "customFields"]
# Test cases imported to root folder ❌

# AFTER
allowed_fields = ["name", "projectKey", ..., "customFields", "folder"]
# Test cases imported to correct folders ✅
```

**Next Steps:**
1. ✅ Folder field is now preserved during import
2. Manually create folder structure in target (or ensure it exists)
3. Re-run step 3 to import test cases with folder assignments
4. Verify test cases appear in correct folders in Jira
