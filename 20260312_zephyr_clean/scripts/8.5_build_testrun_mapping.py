#!/usr/bin/env python3
"""
8.5_build_testrun_mapping.py
--------------------------------
Builds a mapping between SOURCE test run keys and TARGET test run keys
by matching on name, description, and other immutable attributes after import.

This runs AFTER step 8 (import test runs) and BEFORE step 10 (remap test plans).

Input:
  - ~/Desktop/zephyr/exports/testruns_source/ (source test run exports)
  - TARGET instance via API (to fetch newly imported test runs)

Output:
  - ~/Desktop/zephyr/exports/testrun_key_mapping.json
    Format: { "SOURCE-R123": "TARGET-R456", ... }
"""

import json
import os
from datetime import datetime
from config_loader import (
    TARGET_BASE_URL,
    TARGET_PAT,
    TARGET_PROJECT_KEY,
    TLS_CONFIG,
    create_session,
    EXPORT_DIR,
)

# ========= PATHS =========
SOURCE_RUNS_DIR = os.path.join(EXPORT_DIR, "testruns_source")
MAPPING_FILE = os.path.join(EXPORT_DIR, "testrun_key_mapping.json")
# =========================


def normalize_text(text):
    """Normalize text for comparison."""
    if not text:
        return ""
    return str(text).strip().lower()


def build_testrun_signature(run):
    """Create a unique signature for a test run using immutable fields."""
    name = normalize_text(run.get("name", ""))
    desc = normalize_text(run.get("description", ""))

    # Include environment and version as part of signature if they exist
    env = normalize_text(run.get("environment", ""))
    ver = normalize_text(run.get("version", ""))

    # Count of items/test cases
    items = run.get("items", [])
    item_count = len(items) if isinstance(items, list) else 0

    signature = f"{name}||{desc}||env:{env}||ver:{ver}||items:{item_count}"
    return signature


def fetch_target_testruns(session):
    """Fetch all test runs from TARGET project."""
    print(f"📥 Fetching test runs from TARGET ({TARGET_PROJECT_KEY})...")

    all_runs = []
    start_at = 0
    page_size = 200

    while True:
        url = f"{TARGET_BASE_URL}/rest/atm/1.0/testrun/search"
        params = {
            "query": f'projectKey = "{TARGET_PROJECT_KEY}"',
            "startAt": start_at,
            "maxResults": page_size
        }

        resp = session.get(url, params=params, timeout=600)  # 10 minutes for large datasets
        if not resp.ok:
            print(f"⚠️ Error fetching target runs: {resp.status_code}")
            resp.raise_for_status()

        data = resp.json()
        if not data or len(data) == 0:
            break

        # Fetch full details for each run
        for run_summary in data:
            key = run_summary.get("key")
            if key:
                detail_resp = session.get(
                    f"{TARGET_BASE_URL}/rest/atm/1.0/testrun/{key}",
                    timeout=600  # 10 minutes for large test runs
                )
                if detail_resp.ok:
                    all_runs.append(detail_resp.json())

        print(f"  Retrieved {len(all_runs)} test runs so far...")

        if len(data) < page_size:
            break
        start_at += page_size

    print(f"✅ Retrieved {len(all_runs)} test runs from TARGET")
    return all_runs


def load_source_testruns():
    """Load all source test runs from files."""
    print(f"📖 Loading source test runs from {SOURCE_RUNS_DIR}")

    source_runs = []

    if not os.path.exists(SOURCE_RUNS_DIR):
        print(f"⚠️ Source runs directory not found: {SOURCE_RUNS_DIR}")
        return []

    for filename in os.listdir(SOURCE_RUNS_DIR):
        if not filename.endswith(".json"):
            continue

        filepath = os.path.join(SOURCE_RUNS_DIR, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                run_data = json.load(f)

            # Handle different formats
            if isinstance(run_data, list):
                source_runs.extend(run_data)
            elif isinstance(run_data, dict):
                source_runs.append(run_data)

        except Exception as e:
            print(f"⚠️ Error reading {filename}: {e}")

    print(f"✅ Loaded {len(source_runs)} source test runs")
    return source_runs


def build_mapping(source_runs, target_runs):
    """Build mapping from source run keys to target run keys using signatures."""
    print("🔨 Building source→target test run mapping...")

    # Build signature index for target runs
    target_sig_map = {}
    target_keys_used = set()

    for run in target_runs:
        sig = build_testrun_signature(run)
        key = run.get("key")
        if sig and key:
            if sig not in target_sig_map:
                target_sig_map[sig] = []
            target_sig_map[sig].append(key)

    print(f"📊 Built {len(target_sig_map)} unique signatures from target runs")

    # Match source runs to target runs
    mapping = {}
    unmatched = []
    duplicate_matches = []

    for run in source_runs:
        source_key = run.get("key")
        if not source_key:
            continue

        sig = build_testrun_signature(run)

        if sig in target_sig_map:
            matched_keys = target_sig_map[sig]

            # Find first unused target key
            target_key = None
            for k in matched_keys:
                if k not in target_keys_used:
                    target_key = k
                    target_keys_used.add(k)
                    break

            if target_key:
                mapping[source_key] = target_key
                if len(matched_keys) > 1:
                    duplicate_matches.append({
                        "source": source_key,
                        "signature": sig,
                        "possible_targets": matched_keys
                    })
            else:
                unmatched.append(source_key)
        else:
            unmatched.append(source_key)

    print(f"✅ Mapped {len(mapping)} test runs")

    if unmatched:
        print(f"⚠️ WARNING: {len(unmatched)} source test runs could not be matched:")
        for key in unmatched[:10]:
            print(f"  - {key}")
        if len(unmatched) > 10:
            print(f"  ... and {len(unmatched) - 10} more")

    if duplicate_matches:
        print(f"⚠️ WARNING: {len(duplicate_matches)} runs had multiple potential matches")

    return mapping


def main():
    print("=" * 70)
    print("🔗 Building Test Run Key Mapping (Source → Target)")
    print("=" * 70)

    # Load source test runs
    source_runs = load_source_testruns()

    if not source_runs:
        print("❌ No source test runs found. Run step 5 first.")
        return

    # Fetch target test runs
    session = create_session(TARGET_PAT)
    session.verify = TLS_CONFIG["verify"]
    session.cert = TLS_CONFIG["cert"]

    target_runs = fetch_target_testruns(session)

    if not target_runs:
        print("❌ No target test runs found. Run step 8 first.")
        return

    # Build mapping
    mapping = build_mapping(source_runs, target_runs)

    # Save mapping
    os.makedirs(os.path.dirname(MAPPING_FILE) if os.path.dirname(MAPPING_FILE) else ".", exist_ok=True)
    with open(MAPPING_FILE, "w", encoding="utf-8") as f:
        json.dump(mapping, f, indent=2, ensure_ascii=False)

    print(f"💾 Saved mapping to {MAPPING_FILE}")
    print(f"📈 Coverage: {len(mapping)}/{len(source_runs)} test runs mapped " +
          f"({100*len(mapping)//len(source_runs) if source_runs else 0}%)")

    print("=" * 70)
    print("✅ Mapping complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()