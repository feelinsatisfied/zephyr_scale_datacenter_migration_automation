#!/usr/bin/env python3
"""
6_remap_testrun_ids_v2.py
--------------------------------------------------
Maps old Zephyr testCaseKeys from source instance to the new keys in the target instance.

📄 Input files:
  ~/Desktop/zephyr/exports/testruns_source/    ← Test run exports from source
  ~/Desktop/zephyr/exports/testcases_target/   ← Target test case export (for mapping)

🧩 Output:
  ~/Desktop/zephyr/exports/testruns_remapped/  ← Test runs with updated testCaseKeys

💡 How it works:
  1. Loads all test runs exported from the source.
  2. Builds a mapping between old testCaseKeys (e.g. SOURCE-T123) and new testCaseKeys (e.g. TARGET-T456)
     using the target test case export.
  3. Updates all references in test run JSON files.
"""

import os
import json
import re

# ========= CONFIG =========
BASE_DIR = os.path.expanduser("~/Desktop/zephyr")
SOURCE_RUNS_DIR = os.path.join(BASE_DIR, "exports", "testruns_source")
TARGET_CASES_DIR = os.path.join(BASE_DIR, "exports", "testcases_target")
OUTPUT_DIR = os.path.join(BASE_DIR, "exports", "testruns_remapped")

os.makedirs(OUTPUT_DIR, exist_ok=True)
# ==========================


def load_mapping(target_dir):
    """Create a mapping of oldKey → newKey from target test case export files."""
    mapping = {}
    print("🔍 Building key mapping from target test case exports...")
    for file in os.listdir(target_dir):
        if not file.endswith(".json"):
            continue
        path = os.path.join(target_dir, file)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for case in data.get("values", []) or data.get("testCases", []):
                old_key = case.get("oldKey") or case.get("legacyKey") or None
                new_key = case.get("key")
                if old_key and new_key:
                    mapping[old_key] = new_key
        except Exception as e:
            print(f"⚠️ Error reading {file}: {e}")
    print(f"✅ Built mapping of {len(mapping)} case keys.")
    return mapping


def remap_keys_in_run(run_data, mapping):
    """Recursively update testCaseKey references using the provided mapping."""
    if isinstance(run_data, dict):
        for k, v in list(run_data.items()):
            if k == "testCaseKey" and isinstance(v, str):
                if v in mapping:
                    run_data[k] = mapping[v]
                else:
                    # Remove invalid or unmapped references
                    print(f"⚠️ Unmapped testCaseKey: {v}")
                    run_data[k] = None
            else:
                remap_keys_in_run(v, mapping)
    elif isinstance(run_data, list):
        for item in run_data:
            remap_keys_in_run(item, mapping)
    return run_data


def main():
    print("🚀 Remapping testCaseKeys in exported test runs...")
    mapping = load_mapping(TARGET_CASES_DIR)
    total_files = 0
    updated = 0

    for file in os.listdir(SOURCE_RUNS_DIR):
        if not file.endswith(".json"):
            continue
        total_files += 1
        src_path = os.path.join(SOURCE_RUNS_DIR, file)
        out_path = os.path.join(OUTPUT_DIR, file)

        try:
            with open(src_path, "r", encoding="utf-8") as f:
                run_data = json.load(f)

            remapped_data = remap_keys_in_run(run_data, mapping)

            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(remapped_data, f, indent=2, ensure_ascii=False)

            updated += 1
            print(f"✅ Remapped → {file}")

        except Exception as e:
            print(f"⚠️ Failed to process {file}: {e}")

    print(f"\n🏁 Done: {updated}/{total_files} test runs remapped.")
    print(f"📁 Output saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
