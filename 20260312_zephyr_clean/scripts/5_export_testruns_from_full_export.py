#!/usr/bin/env python3
"""
5_export_testruns_from_full_export.py
--------------------------------------
Extracts test runs from the full export and saves them as individual files
for remapping in step 6.

This script reads from the full export created in step 1 and splits out
the test runs into separate files.

Input:
  - ~/Desktop/zephyr/exports/zephyr_scale_full_export.json

Output:
  - ~/Desktop/zephyr/exports/testruns_source/*.json (one file per test run)
"""

import json
import os
from pathlib import Path

# ========= CONFIG =========
BASE_PATH = Path.home() / "Desktop" / "zephyr"
EXPORT_DIR = BASE_PATH / "exports"
FULL_EXPORT_FILE = EXPORT_DIR / "zephyr_scale_full_export.json"
RUNS_OUTPUT_DIR = EXPORT_DIR / "testruns_source"
# ==========================

def main():
    print("=" * 70)
    print("📦 Extracting Test Runs from Full Export")
    print("=" * 70)

    # Check if full export exists
    if not FULL_EXPORT_FILE.exists():
        print(f"❌ Full export file not found: {FULL_EXPORT_FILE}")
        print("   Run step 1 first to export source data.")
        return

    # Load full export
    print(f"📖 Loading full export from {FULL_EXPORT_FILE}")
    with open(FULL_EXPORT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Extract test runs
    test_runs = data.get("testRuns", [])
    if not test_runs:
        print("⚠️ No test runs found in export file.")
        print("   This is normal if your project has no test runs/cycles.")
        print("   Skipping test run export.")
        # Create empty directory so orchestrator doesn't fail
        RUNS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        return

    print(f"📊 Found {len(test_runs)} test runs in export")

    # Create output directory
    RUNS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Save each test run as a separate file
    for i, run in enumerate(test_runs, 1):
        run_key = run.get("key", f"run_{i}")
        run_name = run.get("name", "unnamed")

        filename = f"{run_key}.json"
        filepath = RUNS_OUTPUT_DIR / filename

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(run, f, indent=2, ensure_ascii=False)

        print(f"  ✅ Saved: {filename} - {run_name}")

    print()
    print("=" * 70)
    print(f"📁 Output directory: {RUNS_OUTPUT_DIR}")
    print(f"✅ Extracted {len(test_runs)} test runs")
    print("=" * 70)


if __name__ == "__main__":
    main()