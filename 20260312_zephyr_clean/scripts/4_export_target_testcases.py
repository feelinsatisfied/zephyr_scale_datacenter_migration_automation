#!/usr/bin/env python3
"""
4_export_target_testcases_v2.py
Exports all Zephyr Scale test cases from the target Jira Data Center instance
and builds a mapping table of { testCaseKey: id } for run remapping.
"""

import json
import os
import time
import requests
from config_loader import (
    TARGET_BASE_URL,
    TARGET_PAT,
    TARGET_PROJECT_KEY,
    TLS_CONFIG,
    create_session,
    EXPORT_DIR,
)

# ========= OUTPUT PATHS =========
OUT_FILE = os.path.join(EXPORT_DIR, "target_testcases.json")
MAP_FILE = os.path.join(EXPORT_DIR, "target_testcase_id_map.json")
# ================================


def fetch_all_testcases(session, base_url, project_key, page_size=200):
    """Fetch all Zephyr test cases for the given project."""
    all_cases = []
    start_at = 0
    while True:
        url = f"{base_url}/rest/atm/1.0/testcase"
        params = {"projectKey": project_key, "startAt": start_at, "maxResults": page_size}
        for attempt in range(5):
            resp = session.get(url, params=params, timeout=60)
            if resp.ok:
                break
            print(f"⚠️ Fetch retry ({attempt + 1}/5): {resp.status_code}")
            time.sleep(2 ** attempt)
        resp.raise_for_status()

        data = resp.json()
        values = data.get("values", data if isinstance(data, list) else [])
        if not values:
            break

        all_cases.extend(values)
        print(f"📄 Retrieved {len(values)} (total {len(all_cases)})")

        if len(values) < page_size:
            break
        start_at += page_size

    return all_cases


def build_key_id_map(testcases):
    """Build mapping of testCaseKey → Zephyr internal ID."""
    mapping = {}
    for tc in testcases:
        key = tc.get("key") or tc.get("testCaseKey")
        zid = tc.get("id")
        if key and zid is not None:
            mapping[key] = zid
    return mapping


def main():
    print(f"🌐 Target Jira: {TARGET_BASE_URL}")
    print(f"📁 Project: {TARGET_PROJECT_KEY}")
    print(f"💾 Output → {OUT_FILE}")
    print(f"💾 ID Map → {MAP_FILE}")

    session = create_session(TARGET_PAT)
    session.verify = TLS_CONFIG["verify"]
    session.cert = TLS_CONFIG["cert"]

    print(f"➡️  Exporting all test cases from target project {TARGET_PROJECT_KEY} ...")
    cases = fetch_all_testcases(session, TARGET_BASE_URL, TARGET_PROJECT_KEY)
    print(f"✅ Retrieved {len(cases)} test cases")

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(cases, f, indent=2, ensure_ascii=False)
    print(f"💾 Saved full export → {OUT_FILE}")

    mapping = build_key_id_map(cases)
    with open(MAP_FILE, "w", encoding="utf-8") as f:
        json.dump(mapping, f, indent=2, ensure_ascii=False)
    print(f"💾 Saved key→id map → {MAP_FILE}")

    print("✅ Export completed successfully.")


if __name__ == "__main__":
    main()
