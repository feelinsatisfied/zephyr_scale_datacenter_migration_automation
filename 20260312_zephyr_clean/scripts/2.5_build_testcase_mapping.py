#!/usr/bin/env python3
"""
2.5_build_testcase_mapping.py
--------------------------------
Builds a mapping between SOURCE test case keys and TARGET test case keys
by matching on immutable attributes after import.

This runs AFTER step 3 (import) and BEFORE step 5 (export runs).

Input:
  - ~/Desktop/zephyr/exports/testcases_source/testcases_source.json (source export)
  - TARGET instance via API (to fetch newly imported test cases)

Output:
  - ~/Desktop/zephyr/exports/testcase_key_mapping.json
    Format: { "SOURCE-T123": "TARGET-T456", ... }
"""

import json
import os
from config_loader import (
    TARGET_BASE_URL,
    TARGET_PAT,
    TARGET_PROJECT_KEY,
    SOURCE_PROJECT_KEY,
    TLS_CONFIG,
    create_session,
    EXPORT_DIR,
)

# ========= PATHS =========
# Step 1 outputs to zephyr_scale_full_export.json, not a separate testcases_source folder
SOURCE_CASES_FILE = os.path.join(EXPORT_DIR, "zephyr_scale_full_export.json")
MAPPING_FILE = os.path.join(EXPORT_DIR, "testcase_key_mapping.json")
# =========================


def normalize_text(text):
    """Normalize text for comparison (handle None, whitespace, case)."""
    if not text:
        return ""
    return str(text).strip().lower()


def build_testcase_signature(tc):
    """Create a unique signature for a test case using immutable fields."""
    # Use name + description + first few steps as signature
    name = normalize_text(tc.get("name", ""))
    desc = normalize_text(tc.get("description", "") or tc.get("objective", ""))

    # Get test script steps for additional uniqueness
    steps_sig = ""
    test_script = tc.get("testScript", {})
    if isinstance(test_script, dict):
        steps = test_script.get("steps", [])
        if steps and isinstance(steps, list):
            # Take first 2 steps as part of signature
            for i, step in enumerate(steps[:2]):
                if isinstance(step, dict):
                    step_desc = normalize_text(step.get("description", ""))
                    steps_sig += f"|step{i}:{step_desc}"

    signature = f"{name}||{desc}{steps_sig}"
    return signature


def fetch_target_testcases(session):
    """Fetch all test cases from TARGET project."""
    print(f"📥 Fetching test cases from TARGET ({TARGET_PROJECT_KEY})...")
    print(f"⚠️  This will take ~10-15 minutes for large projects (fetching full details for signature matching)")

    all_cases = []
    start_at = 0
    page_size = 200
    total_fetched = 0

    while True:
        url = f"{TARGET_BASE_URL}/rest/atm/1.0/testcase/search"
        params = {
            "query": f'projectKey = "{TARGET_PROJECT_KEY}"',
            "startAt": start_at,
            "maxResults": page_size
        }

        resp = session.get(url, params=params, timeout=120)
        if not resp.ok:
            print(f"⚠️ Error fetching target cases: {resp.status_code}")
            resp.raise_for_status()

        data = resp.json()
        if not data or len(data) == 0:
            break

        # Fetch full details for each case (needed for testScript/steps in signature)
        batch_size = len(data)
        for i, tc_summary in enumerate(data, 1):
            key = tc_summary.get("key")
            if key:
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        detail_resp = session.get(
                            f"{TARGET_BASE_URL}/rest/atm/1.0/testcase/{key}",
                            timeout=60
                        )
                        if detail_resp.ok:
                            all_cases.append(detail_resp.json())
                            total_fetched += 1

                            # Progress update every 100 cases
                            if total_fetched % 100 == 0:
                                print(f"  📊 Progress: {total_fetched} test cases fetched...")
                            break
                        else:
                            if attempt < max_retries - 1:
                                print(f"⚠️ Failed to fetch {key} (attempt {attempt+1}/{max_retries}), retrying...")
                            else:
                                print(f"⚠️ Skipping {key} after {max_retries} attempts")
                            break
                    except Exception as e:
                        if attempt < max_retries - 1:
                            print(f"⚠️ Error fetching {key} (attempt {attempt+1}/{max_retries}): {e}")
                        else:
                            print(f"❌ Skipping {key} after {max_retries} attempts")

        print(f"  ✓ Batch complete: {len(all_cases)} total test cases retrieved")

        if len(data) < page_size:
            break
        start_at += page_size

    print(f"✅ Retrieved {len(all_cases)} test cases from TARGET")
    return all_cases


def build_mapping(source_cases, target_cases):
    """Build mapping from source keys to target keys using signatures."""
    print("🔨 Building source→target mapping...")

    # Build signature index for target cases
    target_sig_map = {}
    target_keys_used = set()

    for tc in target_cases:
        sig = build_testcase_signature(tc)
        key = tc.get("key")
        if sig and key:
            # Handle duplicates by keeping a list
            if sig not in target_sig_map:
                target_sig_map[sig] = []
            target_sig_map[sig].append(key)

    print(f"📊 Built {len(target_sig_map)} unique signatures from target")

    # Match source cases to target cases
    mapping = {}
    unmatched = []
    duplicate_matches = []

    for tc in source_cases:
        source_key = tc.get("key")
        if not source_key:
            continue

        sig = build_testcase_signature(tc)

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
                # All matches already used
                unmatched.append(source_key)
        else:
            unmatched.append(source_key)

    print(f"✅ Mapped {len(mapping)} test cases")

    if unmatched:
        print(f"⚠️ WARNING: {len(unmatched)} source test cases could not be matched:")
        for key in unmatched[:10]:  # Show first 10
            print(f"  - {key}")
        if len(unmatched) > 10:
            print(f"  ... and {len(unmatched) - 10} more")

    if duplicate_matches:
        print(f"⚠️ WARNING: {len(duplicate_matches)} cases had multiple potential matches")
        print(f"   First match was used. Review if needed.")

    return mapping


def main():
    print("=" * 70)
    print("🔗 Building Test Case Key Mapping (Source → Target)")
    print("=" * 70)

    # Load source test cases
    if not os.path.exists(SOURCE_CASES_FILE):
        print(f"❌ Source test cases file not found: {SOURCE_CASES_FILE}")
        print("   Run step 1 first to export source test cases.")
        return

    print(f"📖 Loading source test cases from {SOURCE_CASES_FILE}")
    with open(SOURCE_CASES_FILE, "r", encoding="utf-8") as f:
        source_data = json.load(f)

    # Handle different formats
    if isinstance(source_data, dict):
        source_cases = source_data.get("testCases", [])
    elif isinstance(source_data, list):
        source_cases = source_data
    else:
        print(f"❌ Unexpected source data format")
        return

    print(f"📊 Loaded {len(source_cases)} source test cases")

    # Fetch target test cases
    session = create_session(TARGET_PAT)
    session.verify = TLS_CONFIG["verify"]
    session.cert = TLS_CONFIG["cert"]

    target_cases = fetch_target_testcases(session)

    # Build mapping
    mapping = build_mapping(source_cases, target_cases)

    # Save mapping
    os.makedirs(os.path.dirname(MAPPING_FILE) if os.path.dirname(MAPPING_FILE) else ".", exist_ok=True)
    with open(MAPPING_FILE, "w", encoding="utf-8") as f:
        json.dump(mapping, f, indent=2, ensure_ascii=False)

    print(f"💾 Saved mapping to {MAPPING_FILE}")
    print(f"📈 Coverage: {len(mapping)}/{len(source_cases)} test cases mapped " +
          f"({100*len(mapping)//len(source_cases) if source_cases else 0}%)")

    print("=" * 70)
    print("✅ Mapping complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()