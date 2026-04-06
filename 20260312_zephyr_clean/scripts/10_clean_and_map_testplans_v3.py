#!/usr/bin/env python3
"""
10_clean_and_map_testplans_v3.py
---------------------------------
Cleans and remaps Zephyr Scale test plan JSONs before importing to TARGET.

Remaps:
  - Test case keys (using testcase_key_mapping.json from step 2.5)
  - Test run keys (using testrun_key_mapping.json from step 8.5)

Input:
  - ~/Desktop/zephyr/exports/zephyr_scale_full_export.json (from step 1)
  - ~/Desktop/zephyr/exports/testcase_key_mapping.json
  - ~/Desktop/zephyr/exports/testrun_key_mapping.json

Output:
  - ~/Desktop/zephyr/exports/testplans_clean/
"""

import os
import json
import glob
from config_loader import TARGET_PROJECT_KEY, EXPORT_DIR

# ========= CONFIG =========
FULL_EXPORT_FILE = os.path.join(EXPORT_DIR, "zephyr_scale_full_export.json")  # Step 1 output
OUT_DIR = os.path.join(EXPORT_DIR, "testplans_clean")
TESTCASE_MAP_FILE = os.path.join(EXPORT_DIR, "testcase_key_mapping.json")
TESTRUN_MAP_FILE = os.path.join(EXPORT_DIR, "testrun_key_mapping.json")
# ==========================

os.makedirs(OUT_DIR, exist_ok=True)

FORBIDDEN_FIELDS = {
    "id", "projectId", "createdBy", "createdOn",
    "modifiedBy", "modifiedOn", "updatedBy", "updatedOn",
    "key",  # Remove old key - will be assigned new one on import
    "comments",  # Not accepted by TARGET API
    "owner"  # User IDs from SOURCE don't exist in TARGET
}


def deep_clean(obj):
    """Recursively remove forbidden metadata fields."""
    if isinstance(obj, dict):
        for k in list(obj.keys()):
            if k in FORBIDDEN_FIELDS:
                obj.pop(k, None)
            else:
                deep_clean(obj[k])
    elif isinstance(obj, list):
        for i in obj:
            deep_clean(i)


def remap_testcase_keys(plan, testcase_map, stats):
    """Replace linked test case keys using the provided mapping."""
    if "testCases" not in plan:
        return

    remapped = []
    for tc_ref in plan.get("testCases", []):
        old_key = tc_ref.get("key") or tc_ref.get("testCaseKey")

        if old_key and old_key in testcase_map:
            new_key = testcase_map[old_key]
            remapped.append({"testCaseKey": new_key})
            stats["testcases_remapped"] += 1
        else:
            if old_key:
                stats["testcases_unmapped"].add(old_key)

    plan["testCases"] = remapped


def remap_testrun_keys(plan, testrun_map, stats):
    """Replace linked test run keys using the provided mapping."""
    if "testRuns" not in plan:
        return

    remapped = []
    for run_ref in plan.get("testRuns", []):
        old_key = run_ref.get("key") or run_ref.get("testRunKey")

        if old_key and old_key in testrun_map:
            new_key = testrun_map[old_key]
            remapped.append({"testRunKey": new_key})
            stats["testruns_remapped"] += 1
        else:
            if old_key:
                stats["testruns_unmapped"].add(old_key)

    plan["testRuns"] = remapped


def process_testplan(plan, testcase_map, testrun_map):
    """Clean and remap a single test plan."""
    stats = {
        "testcases_remapped": 0,
        "testruns_remapped": 0,
        "testcases_unmapped": set(),
        "testruns_unmapped": set()
    }

    # Remap test case and test run references BEFORE cleaning
    # (deep_clean removes keys which we need for remapping)
    remap_testcase_keys(plan, testcase_map, stats)
    remap_testrun_keys(plan, testrun_map, stats)

    # Clean forbidden fields AFTER remapping
    deep_clean(plan)

    # Set target project key
    plan["projectKey"] = TARGET_PROJECT_KEY

    return plan, stats


def main():
    print("=" * 70)
    print("🧹 Cleaning and Remapping Test Plans")
    print("=" * 70)

    # Check if full export exists
    if not os.path.exists(FULL_EXPORT_FILE):
        print(f"❌ Full export not found: {FULL_EXPORT_FILE}")
        print("   Run step 1 first to export all data from source.")
        return

    # Load test plans from step 1 full export
    print(f"📖 Loading test plans from step 1 export: {FULL_EXPORT_FILE}")
    with open(FULL_EXPORT_FILE, "r", encoding="utf-8") as f:
        full_export = json.load(f)

    test_plans = full_export.get("testPlans", [])
    if not test_plans:
        print("⚠️ No test plans found in step 1 export.")
        print("   Your project may not have any test plans.")
        return

    print(f"📊 Found {len(test_plans)} test plans in step 1 export")

    # Load test case mapping
    if not os.path.exists(TESTCASE_MAP_FILE):
        print(f"⚠️ Test case mapping not found: {TESTCASE_MAP_FILE}")
        print("   Run step 2.5 first. Continuing without test case remapping...")
        testcase_map = {}
    else:
        with open(TESTCASE_MAP_FILE, "r", encoding="utf-8") as f:
            testcase_map = json.load(f)
        print(f"✅ Loaded {len(testcase_map)} test case key mappings")

    # Load test run mapping
    if not os.path.exists(TESTRUN_MAP_FILE):
        print(f"⚠️ Test run mapping not found: {TESTRUN_MAP_FILE}")
        print("   Run step 8.5 first. Continuing without test run remapping...")
        testrun_map = {}
    else:
        with open(TESTRUN_MAP_FILE, "r", encoding="utf-8") as f:
            testrun_map = json.load(f)
        print(f"✅ Loaded {len(testrun_map)} test run key mappings")

    total_stats = {
        "testcases_remapped": 0,
        "testruns_remapped": 0,
        "testcases_unmapped": set(),
        "testruns_unmapped": set()
    }

    print()
    for i, plan in enumerate(test_plans, 1):
        try:
            # Save plan name and key BEFORE processing (deep_clean will remove key)
            plan_name = plan.get("name", f"plan_{i}")
            plan_key = plan.get("key", f"plan_{i}")

            cleaned_plan, stats = process_testplan(plan, testcase_map, testrun_map)

            # Update totals
            total_stats["testcases_remapped"] += stats["testcases_remapped"]
            total_stats["testruns_remapped"] += stats["testruns_remapped"]
            total_stats["testcases_unmapped"].update(stats["testcases_unmapped"])
            total_stats["testruns_unmapped"].update(stats["testruns_unmapped"])

            # Save cleaned plan
            out_filename = f"testplan_{plan_key}.json"
            out_path = os.path.join(OUT_DIR, out_filename)

            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(cleaned_plan, f, indent=2, ensure_ascii=False)

            print(f"✅ {plan_name} ({plan_key})")
            print(f"   Test cases: {stats['testcases_remapped']} remapped, " +
                  f"{len(stats['testcases_unmapped'])} unmapped")
            print(f"   Test runs: {stats['testruns_remapped']} remapped, " +
                  f"{len(stats['testruns_unmapped'])} unmapped")

        except Exception as e:
            print(f"❌ Error processing plan {i}: {e}")

    print()
    print("=" * 70)
    print("📊 Summary:")
    print(f"   Plans processed: {len(test_plans)}")
    print(f"   Test case references remapped: {total_stats['testcases_remapped']}")
    print(f"   Test run references remapped: {total_stats['testruns_remapped']}")

    if total_stats["testcases_unmapped"]:
        print(f"\n⚠️ {len(total_stats['testcases_unmapped'])} test case keys could not be mapped:")
        for key in sorted(list(total_stats["testcases_unmapped"]))[:10]:
            print(f"   - {key}")
        if len(total_stats["testcases_unmapped"]) > 10:
            print(f"   ... and {len(total_stats['testcases_unmapped']) - 10} more")

    if total_stats["testruns_unmapped"]:
        print(f"\n⚠️ {len(total_stats['testruns_unmapped'])} test run keys could not be mapped:")
        for key in sorted(list(total_stats["testruns_unmapped"]))[:10]:
            print(f"   - {key}")
        if len(total_stats["testruns_unmapped"]) > 10:
            print(f"   ... and {len(total_stats['testruns_unmapped']) - 10} more")

    print(f"\n💾 Output saved to: {OUT_DIR}")
    print("=" * 70)
    print("✅ Test plans ready for import!")
    print("=" * 70)


if __name__ == "__main__":
    main()
