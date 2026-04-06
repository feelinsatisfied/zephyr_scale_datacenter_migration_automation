#!/usr/bin/env python3
"""
6_remap_testrun_ids_v3.py
--------------------------------------------------
Remaps source test case keys to target test case keys in test run JSONs.

Uses the mapping built in step 2.5 (testcase_key_mapping.json) to update
all testCaseKey references in test runs.

Input:
  - ~/Desktop/zephyr/exports/testruns_source/     ← Test runs from source
  - ~/Desktop/zephyr/exports/testcase_key_mapping.json  ← Key mapping

Output:
  - ~/Desktop/zephyr/exports/testruns_remapped/   ← Runs with updated keys
"""

import os
import json

# ========= CONFIG =========
BASE_DIR = os.path.expanduser("~/Desktop/zephyr")
EXPORT_DIR = os.path.join(BASE_DIR, "exports")

SOURCE_RUNS_DIR = os.path.join(EXPORT_DIR, "testruns_source")
MAPPING_FILE = os.path.join(EXPORT_DIR, "testcase_key_mapping.json")
OUTPUT_DIR = os.path.join(EXPORT_DIR, "testruns_remapped")

os.makedirs(OUTPUT_DIR, exist_ok=True)
# ==========================


def remap_keys_recursive(obj, mapping, stats):
    """
    Recursively find and remap testCaseKey references.

    Args:
        obj: JSON object (dict/list) to process
        mapping: Dict of source_key → target_key
        stats: Dict to track remapping statistics
    """
    if isinstance(obj, dict):
        for k, v in list(obj.items()):
            if k == "testCaseKey" and isinstance(v, str):
                if v in mapping:
                    new_key = mapping[v]
                    obj[k] = new_key
                    stats["remapped"] += 1
                    stats["mappings"].add(f"{v} → {new_key}")
                else:
                    # Unmapped key - remove it or keep as-is?
                    # Option 1: Remove (safer for import)
                    stats["unmapped"].add(v)
                    obj[k] = None  # Set to null; will be cleaned later
                    stats["removed"] += 1
            else:
                remap_keys_recursive(v, mapping, stats)

    elif isinstance(obj, list):
        for item in obj:
            remap_keys_recursive(item, mapping, stats)

    return obj


def clean_null_testcase_refs(obj):
    """Remove items with null testCaseKey to avoid import errors."""
    if isinstance(obj, dict):
        # Remove null testCaseKey from dict
        if "testCaseKey" in obj and obj["testCaseKey"] is None:
            obj.pop("testCaseKey", None)

        # Recurse into nested structures
        for k, v in list(obj.items()):
            clean_null_testcase_refs(v)

    elif isinstance(obj, list):
        # Remove list items that have null testCaseKey
        items_to_remove = []
        for i, item in enumerate(obj):
            if isinstance(item, dict) and item.get("testCaseKey") is None:
                items_to_remove.append(i)
            else:
                clean_null_testcase_refs(item)

        # Remove in reverse to maintain indices
        for i in reversed(items_to_remove):
            obj.pop(i)

    return obj


def process_testrun_file(filepath, mapping, output_path):
    """Process a single test run JSON file."""
    stats = {
        "remapped": 0,
        "removed": 0,
        "unmapped": set(),
        "mappings": set()
    }

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            run_data = json.load(f)

        # Remap all testCaseKey references
        remap_keys_recursive(run_data, mapping, stats)

        # Clean up null references
        clean_null_testcase_refs(run_data)

        # Save remapped file
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(run_data, f, indent=2, ensure_ascii=False)

        return stats

    except Exception as e:
        print(f"❌ Error processing {os.path.basename(filepath)}: {e}")
        return None


def main():
    print("=" * 70)
    print("🔄 Remapping Test Run Test Case Keys")
    print("=" * 70)

    # Load mapping
    if not os.path.exists(MAPPING_FILE):
        print(f"❌ Mapping file not found: {MAPPING_FILE}")
        print("   Run step 2.5 (build_testcase_mapping.py) first!")
        return

    print(f"📖 Loading mapping from {MAPPING_FILE}")
    with open(MAPPING_FILE, "r", encoding="utf-8") as f:
        mapping = json.load(f)
    print(f"✅ Loaded {len(mapping)} test case key mappings")

    # Check source runs directory
    if not os.path.exists(SOURCE_RUNS_DIR):
        print(f"❌ Source runs directory not found: {SOURCE_RUNS_DIR}")
        print("   Run step 5 (export test runs) first!")
        return

    # Get all JSON files
    run_files = [f for f in os.listdir(SOURCE_RUNS_DIR) if f.endswith(".json")]
    if not run_files:
        print(f"⚠️ No JSON files found in {SOURCE_RUNS_DIR}")
        return

    print(f"📂 Found {len(run_files)} test run files")
    print()

    # Process each file
    total_remapped = 0
    total_removed = 0
    all_unmapped = set()
    files_processed = 0

    for run_file in run_files:
        source_path = os.path.join(SOURCE_RUNS_DIR, run_file)
        output_path = os.path.join(OUTPUT_DIR, run_file)

        stats = process_testrun_file(source_path, mapping, output_path)

        if stats:
            files_processed += 1
            total_remapped += stats["remapped"]
            total_removed += stats["removed"]
            all_unmapped.update(stats["unmapped"])

            status = "✅" if stats["remapped"] > 0 else "⚪"
            print(f"{status} {run_file}: {stats['remapped']} remapped, {stats['removed']} removed")

    print()
    print("=" * 70)
    print(f"📊 Summary:")
    print(f"   Files processed: {files_processed}/{len(run_files)}")
    print(f"   Total testCaseKey remapped: {total_remapped}")
    print(f"   Total unmapped (removed): {total_removed}")

    if all_unmapped:
        print(f"\n⚠️ WARNING: {len(all_unmapped)} unique test case keys could not be mapped:")
        for key in sorted(list(all_unmapped))[:15]:
            print(f"   - {key}")
        if len(all_unmapped) > 15:
            print(f"   ... and {len(all_unmapped) - 15} more")
        print()
        print("   These test cases may not have been imported to the target.")
        print("   Test run items referencing these cases were removed.")

    print(f"\n💾 Output saved to: {OUTPUT_DIR}")
    print("=" * 70)
    print("✅ Remapping complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()