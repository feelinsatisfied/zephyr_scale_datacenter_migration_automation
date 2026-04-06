#!/usr/bin/env python3
"""
7_clean_testruns_for_import_v2.py
----------------------------------
Final cleanup pass for Zephyr test run JSONs before import to the target instance.

• Loads config automatically from ~/Desktop/zephyr/config
• Reads from ~/Desktop/zephyr/exports/testruns_remapped
• Outputs to ~/Desktop/zephyr/exports/runs_clean
• Removes all Zephyr Data Center forbidden fields
• Normalizes folder references and testCase link structures
"""

import os
import json
import glob
from config_loader import EXPORT_DIR

# ========= CONFIG =========
IN_DIR = os.path.join(EXPORT_DIR, "testruns_remapped")
OUT_DIR = os.path.join(EXPORT_DIR, "runs_clean")
# ==========================

os.makedirs(OUT_DIR, exist_ok=True)

FORBIDDEN_FIELDS = {
    "id", "key", "projectId", "testRuns", "createdBy", "createdOn",
    "modifiedBy", "modifiedOn", "updatedBy", "updatedOn",
    "executionSummary", "issueCount", "executionTime",
    "testCaseCount", "owner", "estimatedTime", "results",
    "environment"  # Not recognized by TARGET API
}


def deep_clean(obj, parent_key=None):
    """Recursively remove forbidden Zephyr fields."""
    if isinstance(obj, dict):
        for k in list(obj.keys()):
            if k in FORBIDDEN_FIELDS:
                obj.pop(k, None)
                continue
            deep_clean(obj[k], parent_key=k)
    elif isinstance(obj, list):
        for i in obj:
            deep_clean(i, parent_key)


def clean_run(run: dict):
    """Clean and normalize one test run JSON structure."""
    deep_clean(run)

    # Folders should remain strings (not dict objects)
    folder = run.get("folder")
    if isinstance(folder, dict):
        run["folder"] = folder.get("name")

    # Ensure testCase references are structured properly and clean user references
    if "items" in run:
        for item in run["items"]:
            # Remove user references from test result items (users don't exist in TARGET)
            for user_field in ["userKey", "executedBy", "assignedTo"]:
                item.pop(user_field, None)

            # Ensure testCase.id exists - create from testCaseKey if needed
            tc = item.get("testCase", {})
            testcase_key = item.get("testCaseKey")

            if not isinstance(tc, dict):
                # testCase is not a dict, coerce it
                if testcase_key:
                    item["testCase"] = {"id": testcase_key}
                else:
                    print(f"⚠️ Missing both testCase and testCaseKey in run item '{run.get('name')}'")
            elif "id" not in tc or not tc.get("id"):
                # testCase is a dict but missing id field
                if testcase_key:
                    tc["id"] = testcase_key
                else:
                    print(f"⚠️ Missing testCase.id and testCaseKey in run item '{run.get('name')}'")

    return run


def main():
    run_files = glob.glob(os.path.join(IN_DIR, "*.json"))
    print(f"🔍 Found {len(run_files)} remapped test run files in {IN_DIR}")

    if not run_files:
        print("⚠️ No run files found! Please ensure script 6 has been executed first.")
        return

    for rf in run_files:
        with open(rf, "r", encoding="utf-8") as f:
            run = json.load(f)

        run = clean_run(run)

        out_path = os.path.join(OUT_DIR, os.path.basename(rf))
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(run, f, indent=2, ensure_ascii=False)

        print(f"✅ Cleaned and saved → {out_path}")

    print(f"🏁 All test runs cleaned and ready for import in → {OUT_DIR}")


if __name__ == "__main__":
    main()
