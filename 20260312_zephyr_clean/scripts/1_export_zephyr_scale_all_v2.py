#!/usr/bin/env python3
"""
1_export_zephyr_scale_all_v3.py
Export Zephyr Scale data (test cases, test plans, test runs + results)
from a Jira Data Center source instance using config_loader.
"""

import json
import os
import time
import requests
from config_loader import (
    SOURCE_BASE_URL,
    SOURCE_PAT,
    SOURCE_PROJECT_KEY,
    TLS_CONFIG,
    create_session,
    EXPORT_DIR,
)

# ========= SETTINGS =========
PAGE_SIZE = 50  # Reduced from 100 for better reliability with large datasets
REQUEST_TIMEOUT = 600  # 10 minutes per request (for slow server responses)
MAX_RETRIES = 3  # Number of retry attempts for failed requests
OUT_FILE = os.path.join(EXPORT_DIR, "zephyr_scale_full_export.json")
# ============================

session = create_session(SOURCE_PAT)

print(f"🌐 Source Jira: {SOURCE_BASE_URL}")
print(f"📁 Project Key: {SOURCE_PROJECT_KEY}")
print(f"📤 Output File: {OUT_FILE}")

# ---- API Endpoints ----
TC_SEARCH = f"{SOURCE_BASE_URL}/rest/atm/1.0/testcase/search"
TC_GET = f"{SOURCE_BASE_URL}/rest/atm/1.0/testcase"
PLAN_SEARCH = f"{SOURCE_BASE_URL}/rest/atm/1.0/testplan/search"
PLAN_GET = f"{SOURCE_BASE_URL}/rest/atm/1.0/testplan"
RUN_SEARCH = f"{SOURCE_BASE_URL}/rest/atm/1.0/testrun/search"
RUN_GET = f"{SOURCE_BASE_URL}/rest/atm/1.0/testrun"
RESULTS_GET = f"{SOURCE_BASE_URL}/rest/atm/1.0/testrun"

session.verify = TLS_CONFIG["verify"]
session.cert = TLS_CONFIG["cert"]


def fetch_paginated(url, query=None, page_size=None):
    """Generic pagination helper with retry logic."""
    if page_size is None:
        page_size = PAGE_SIZE

    start_at = 0
    all_items = []
    while True:
        params = {"startAt": start_at, "maxResults": page_size}
        if query:
            params["query"] = query

        # Retry logic for transient network errors
        for attempt in range(MAX_RETRIES):
            try:
                print(f"  Fetching items {start_at}-{start_at + page_size}...")
                resp = session.get(url, params=params, timeout=REQUEST_TIMEOUT)
                if resp.status_code == 403:
                    raise SystemExit(f"🚫 403 Forbidden: Check PAT permissions for {url}")
                resp.raise_for_status()
                break  # Success, exit retry loop
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                if attempt < MAX_RETRIES - 1:
                    wait_time = (attempt + 1) * 10  # 10s, 20s, 30s
                    print(f"⚠️ Request timeout/error (attempt {attempt + 1}/{MAX_RETRIES}), retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print(f"❌ Failed after {MAX_RETRIES} attempts")
                    raise

        data = resp.json()
        if not data:
            break
        all_items.extend(data)
        print(f"  ✓ Retrieved {len(data)} items (total so far: {len(all_items)})")
        if len(data) < page_size:
            break
        start_at += page_size
    return all_items


def fetch_testcase_details():
    print(f"📦 Exporting Test Cases from {SOURCE_PROJECT_KEY} ...")
    keys = fetch_paginated(TC_SEARCH, f'projectKey = "{SOURCE_PROJECT_KEY}"')
    details = []
    for i, tc in enumerate(keys, 1):
        key = tc.get("key")
        for attempt in range(MAX_RETRIES):
            try:
                r = session.get(f"{TC_GET}/{key}", timeout=REQUEST_TIMEOUT)
                if not r.ok:
                    print(f"⚠️ Failed to fetch {key}: {r.status_code}")
                    break
                details.append(r.json())
                if i % 50 == 0:
                    print(f"  Progress: {i}/{len(keys)} test cases")
                break
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
                if attempt < MAX_RETRIES - 1:
                    print(f"⚠️ Timeout on {key}, retrying...")
                    time.sleep(5)
                else:
                    print(f"❌ Skipping {key} after {MAX_RETRIES} attempts")
    return details


def fetch_testplans():
    print("📦 Exporting Test Plans ...")
    plans = fetch_paginated(PLAN_SEARCH, f'projectKey = "{SOURCE_PROJECT_KEY}"')
    details = []
    for i, plan in enumerate(plans, 1):
        key = plan.get("key")
        for attempt in range(MAX_RETRIES):
            try:
                r = session.get(f"{PLAN_GET}/{key}", timeout=REQUEST_TIMEOUT)
                if not r.ok:
                    print(f"⚠️ Failed to fetch plan {key}")
                    break
                details.append(r.json())
                if i % 10 == 0:
                    print(f"  Progress: {i}/{len(plans)} test plans")
                break
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
                if attempt < MAX_RETRIES - 1:
                    print(f"⚠️ Timeout on plan {key}, retrying...")
                    time.sleep(5)
                else:
                    print(f"❌ Skipping plan {key} after {MAX_RETRIES} attempts")
    return details


def fetch_testruns_and_results():
    print("📦 Exporting Test Runs and Results (PAGE_SIZE=1 due to large runs)...")
    runs = fetch_paginated(RUN_SEARCH, f'projectKey = "{SOURCE_PROJECT_KEY}"', page_size=1)
    run_objects = []
    for i, run in enumerate(runs, 1):
        key = run.get("key")

        # Fetch test run details with retry
        run_data = None
        for attempt in range(MAX_RETRIES):
            try:
                run_resp = session.get(f"{RUN_GET}/{key}", timeout=REQUEST_TIMEOUT)
                if not run_resp.ok:
                    print(f"⚠️ Failed to fetch run {key}")
                    break
                run_data = run_resp.json()
                break
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
                if attempt < MAX_RETRIES - 1:
                    print(f"⚠️ Timeout on run {key}, retrying...")
                    time.sleep(5)
                else:
                    print(f"❌ Skipping run {key} after {MAX_RETRIES} attempts")

        if not run_data:
            continue

        # Fetch test results with retry
        for attempt in range(MAX_RETRIES):
            try:
                results_resp = session.get(f"{RESULTS_GET}/{key}/testresults", timeout=REQUEST_TIMEOUT)
                if results_resp.ok:
                    run_data["results"] = results_resp.json()
                else:
                    run_data["results"] = []
                break
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
                if attempt < MAX_RETRIES - 1:
                    print(f"⚠️ Timeout fetching results for {key}, retrying...")
                    time.sleep(5)
                else:
                    print(f"⚠️ Skipping results for {key} after {MAX_RETRIES} attempts")
                    run_data["results"] = []

        run_objects.append(run_data)
        if i % 10 == 0:
            print(f"  Progress: {i}/{len(runs)} test runs")
    return run_objects


def main():
    print("⚠️  ATTEMPTING TEST RUNS WITH PAGE_SIZE=1")
    print("    Previous attempts with PAGE_SIZE=50 caused 'Connection reset by peer'")
    print("    Trying PAGE_SIZE=1 to work around large test runs (4685+ test cases)")
    print("")

    export_payload = {
        "testCases": fetch_testcase_details(),
        "testPlans": fetch_testplans(),
        "testRuns": fetch_testruns_and_results(),  # Using PAGE_SIZE=1
    }

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(export_payload, f, indent=2, ensure_ascii=False)

    print(f"✅ Export complete → {OUT_FILE}")
    print(f"   Test Cases: {len(export_payload['testCases'])}")
    print(f"   Test Plans: {len(export_payload['testPlans'])}")
    print(f"   Test Runs: {len(export_payload['testRuns'])}")


if __name__ == "__main__":
    main()
