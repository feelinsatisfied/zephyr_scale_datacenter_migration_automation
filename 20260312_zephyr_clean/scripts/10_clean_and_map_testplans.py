#!/usr/bin/env python3
"""
10_clean_and_map_testplans_v2.py
--------------------------------
Cleans and remaps Zephyr Scale test plan JSONs before importing into the TARGET Jira Data Center instance.

Automatically uses configuration files from:
  ~/Desktop/zephyr/config/
Reads exported plans from:
  ~/Desktop/zephyr/exports/plans_export/
Reads run key mapping file from:
  ~/Desktop/zephyr/exports/run_key_map.json
Outputs cleaned plans to:
  ~/Desktop/zephyr/exports/plans_clean/
"""

import os
import json
import glob

# ========= CONFIG =========
CONFIG_DIR = os.path.expanduser("~/Desktop/zephyr/config")
EXPORT_DIR = os.path.expanduser("~/Desktop/zephyr/exports")

IN_DIR = os.path.join(EXPORT_DIR, "plans_export")
OUT_DIR = os.path.join(EXPORT_DIR, "plans_clean")
RUN_KEY_MAP = os.path.join(EXPORT_DIR, "run_key_map.json")
# ==========================

os.makedirs(OUT_DIR, exist_ok=True)

FORBIDDEN_FIELDS = {
    "id", "projectId", "createdBy", "createdOn",
    "modifiedBy", "modifiedOn", "updatedBy", "updatedOn"
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


def remap_run_keys(plan, run_map):
    """Replace linked test run keys using the provided mapping (old → new)."""
    if "testRuns" not in plan:
        return
    remapped = []
    for run_ref in plan["testRuns"]:
        old_key = run_ref.get("key")
        if old_key and old_key in run_map:
            new_key = run_map[old_key]
            run_ref["key"] = new_key
            remapped.append(new_key)
        else:
            print(f"⚠️ Unmapped test run key: {old_key}")
    plan["testRuns"] = [{"key": k} for k in remapped]


def main():
    print("🔍 Cleaning and remapping Zephyr test plans...")

    # Load mapping (oldRunKey → newRunKey)
    if not os.path.exists(RUN_KEY_MAP):
        print(f"❌ Missing run key map file: {RUN_KEY_MAP}")
        return

    with open(RUN_KEY_MAP, "r", encoding="utf-8") as f:
        run_map = json.load(f)
    print(f"🔁 Loaded {len(run_map)} run key mappings.")

    # Process all plan files
    plan_files = glob.glob(os.path.join(IN_DIR, "testplan_*.json"))
    print(f"📂 Found {len(plan_files)} test plans in {IN_DIR}")

    if not plan_files:
        print("⚠️ No test plans found to clean.")
        return

    for pf in plan_files:
        with open(pf, "r", encoding="utf-8") as f:
            plan = json.load(f)

        deep_clean(plan)
        remap_run_keys(plan, run_map)

        out_path = os.path.join(OUT_DIR, os.path.basename(pf))
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(plan, f, indent=2, ensure_ascii=False)

        print(f"✅ Cleaned & remapped {os.path.basename(pf)}")

    print(f"🏁 Test plans ready for import → {OUT_DIR}")


if __name__ == "__main__":
    main()
