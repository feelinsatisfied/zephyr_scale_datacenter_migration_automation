#!/usr/bin/env python3
"""
2_clean_up_zephyr_scale_all_v6.py
Clean and normalize Zephyr Scale export JSON using shared config from config_loader.py.
Removes forbidden fields, fixes project references, and outputs import-ready data.
"""

import json
import os
from config_loader import TARGET_PROJECT_KEY, EXPORT_DIR

# ========= CONFIG =========
IN_FILE = os.path.join(EXPORT_DIR, "zephyr_scale_full_export.json")
OUT_FILE = os.path.join(EXPORT_DIR, "zephyr_scale_full_clean.json")
# ==========================

FORBIDDEN_FIELDS = {
    "id", "stepId", "index", "testRuns",
    "projectId", "createdBy", "createdOn",
    "modifiedBy", "modifiedOn", "updatedBy", "updatedOn",
    "comments", "estimatedTime", "issueCount", "executionTime",
    "testCaseCount", "testResultId", "executedBy", "executionDate",
    "owner", "issueLinks", "executionSummary"
}


def deep_clean(obj, parent_key=None, grandparent=None):
    """Recursively remove forbidden fields and context-sensitive keys."""
    if isinstance(obj, dict):
        for k in list(obj.keys()):
            if k in FORBIDDEN_FIELDS:
                obj.pop(k, None)
                continue

            # Remove 'key' unless inside issueLinks (valid Jira linkage)
            if k == "key" and parent_key != "issueLinks":
                obj.pop(k, None)
                continue

            # Remove 'id' from Zephyr-specific contexts
            if k == "id" and (parent_key in ("testScript", "steps", "testRuns", "testPlans") or
                              (grandparent in ("testScript", "steps"))):
                obj.pop(k, None)
                continue

            deep_clean(obj[k], parent_key=k, grandparent=parent_key)

    elif isinstance(obj, list):
        for item in obj:
            deep_clean(item, parent_key, grandparent)

    elif isinstance(obj, str):
        if obj.strip().startswith("{") or obj.strip().startswith("["):
            try:
                parsed = json.loads(obj)
                deep_clean(parsed, parent_key, grandparent)
                return json.dumps(parsed)
            except Exception:
                pass
    return obj


def sanitize_testcase(tc):
    deep_clean(tc)
    if "testScript" not in tc or not isinstance(tc["testScript"], dict):
        tc["testScript"] = {"type": "STEP_BY_STEP", "steps": []}
    return tc


def sanitize_testplan(plan):
    deep_clean(plan)
    return plan


def deep_clean_result_ids(obj):
    """Recursively remove any field containing 'id' (case-insensitive) in test result structures."""
    if isinstance(obj, dict):
        for k in list(obj.keys()):
            if "id" == k.lower() or k.lower().endswith("id"):
                obj.pop(k, None)
                continue
            deep_clean_result_ids(obj[k])
    elif isinstance(obj, list):
        for i in obj:
            deep_clean_result_ids(i)


def sanitize_testrun(run):
    """Fully strip forbidden and Zephyr-unsupported fields from test runs."""
    for k in [
        "id", "projectId", "createdBy", "createdOn", "modifiedBy", "modifiedOn",
        "updatedBy", "updatedOn", "estimatedTime", "issueCount", "executionTime",
        "testCaseCount", "executionSummary", "key", "testResults", "testRuns"
    ]:
        run.pop(k, None)

    if "results" in run:
        results = run["results"]
        deep_clean_result_ids(results)
        run.pop("results", None)

    deep_clean_result_ids(run)

    # 🩹 Drop invalid test case references that cause “testCaseKey required” errors
    run.pop("testCaseKey", None)
    run.pop("testCases", None)

    return run


def fix_project_references(obj, target_project=TARGET_PROJECT_KEY):
    """Force projectKey and issueKey references to the target project."""
    if isinstance(obj, dict):
        for k, v in list(obj.items()):
            if k == "projectKey":
                obj[k] = target_project
            elif k == "issueKey" and isinstance(v, str) and "-" in v:
                project_prefix = v.split("-")[0]
                if project_prefix != target_project:
                    obj.pop(k)
            else:
                fix_project_references(v, target_project)
    elif isinstance(obj, list):
        for item in obj:
            fix_project_references(item, target_project)


def remove_invalid_links(obj, valid_project=TARGET_PROJECT_KEY):
    """Remove any issueKey or testCaseKey references pointing to other projects."""
    if isinstance(obj, dict):
        for k, v in list(obj.items()):
            if k in ("issueKey", "testCaseKey") and isinstance(v, str) and not v.startswith(f"{valid_project}-"):
                obj.pop(k)
            else:
                remove_invalid_links(v, valid_project)
    elif isinstance(obj, list):
        for i in obj:
            remove_invalid_links(i, valid_project)


def remove_foreign_refs(obj, valid_project=TARGET_PROJECT_KEY, valid_users=None):
    """Strip testCaseKey, issueKey, or user references from other Jira projects/users."""
    if valid_users is None:
        valid_users = []

    if isinstance(obj, dict):
        for k, v in list(obj.items()):
            if k in ("issueKey", "testCaseKey") and isinstance(v, str) and not v.startswith(f"{valid_project}-"):
                obj.pop(k)
                continue

            if k in ("userKey", "assignedTo", "executedBy", "owner") and isinstance(v, str):
                if v not in valid_users:
                    obj.pop(k)
                    continue

            remove_foreign_refs(v, valid_project, valid_users)

    elif isinstance(obj, list):
        for i in obj:
            remove_foreign_refs(i, valid_project, valid_users)


def main():
    print(f"🧩 Cleaning Zephyr export → {IN_FILE}")
    with open(IN_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    cleaned = {
        "testCases": [sanitize_testcase(tc) for tc in data.get("testCases", [])],
        "testPlans": [sanitize_testplan(p) for p in data.get("testPlans", [])],
        "testRuns": [sanitize_testrun(r) for r in data.get("testRuns", [])]
    }

    fix_project_references(cleaned)
    remove_invalid_links(cleaned)
    remove_foreign_refs(cleaned, valid_users=["JIRAUSER10000"])

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, indent=2, ensure_ascii=False)

    print(f"✅ Cleaned data saved → {OUT_FILE}")
    print("🔎 Verifying forbidden fields ...")

    with open(OUT_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    found = [f for f in ["id", "testRuns", "key"] if f in content]
    if found:
        print(f"⚠️ Still found references to: {found}")
        print("👉 These may remain only in valid contexts (e.g., issueLinks).")
    else:
        print("✅ No forbidden fields remain. Ready for import!")


if __name__ == "__main__":
    main()
