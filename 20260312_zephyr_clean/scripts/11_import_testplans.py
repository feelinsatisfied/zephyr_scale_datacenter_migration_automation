#!/usr/bin/env python3
"""
11_import_testplans_v2.py
---------------------------------
Imports cleaned Zephyr Scale test plans into the TARGET Jira Data Center instance.

Uses centralized configuration from:
  ~/Desktop/zephyr/config/
Reads cleaned plans from:
  ~/Desktop/zephyr/exports/plans_clean/
"""

import os
import json
import time
import requests
from requests.exceptions import RequestException

# ========= CONFIG =========
CONFIG_DIR = os.path.expanduser("~/Desktop/zephyr/config")
EXPORT_DIR = os.path.expanduser("~/Desktop/zephyr/exports/testplans_clean")
CERT_DIR = os.path.expanduser("~/Desktop/zephyr/certs")

# Load credentials and settings
def read_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()

TARGET_BASE_URL = read_file(os.path.join(CONFIG_DIR, "target_base_url.txt"))
TARGET_PAT = read_file(os.path.join(CONFIG_DIR, "target_pat.txt"))
TARGET_PROJECT_KEY = read_file(os.path.join(CONFIG_DIR, "target_proj_key.txt"))

verify_cert = os.path.join(CERT_DIR, "aws_cert_dev.crt")
client_cert = os.path.join(CERT_DIR, "zephyr_cert_test.crt")
client_key = os.path.join(CERT_DIR, "zephyr_pw_key.key")

tls_config = {
    "verify": verify_cert,
    "cert": (client_cert, client_key)
}
# ==========================


def make_session(pat: str) -> requests.Session:
    """Create an authenticated HTTPS session for Zephyr Scale."""
    s = requests.Session()
    s.headers.update({
        "Authorization": f"Bearer {pat}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    })
    s.verify = verify_cert
    s.cert = (client_cert, client_key)
    return s


def import_testplan(session, base_url, project_key, plan):
    """POST a single test plan into the target instance, then PUT to add links."""
    try:
        # Save original plan data before any modifications
        original_plan = plan.copy()

        # Extract test runs and test cases before creating plan
        test_runs = plan.pop("testRuns", [])
        test_cases = plan.pop("testCases", [])

        # Step 1: Create the plan without links
        plan["projectKey"] = project_key
        url = f"{base_url}/rest/atm/1.0/testplan"
        resp = session.post(url, json=plan, timeout=60)
        if not resp.ok:
            print(f"❌ Failed to create plan ({resp.status_code}): {resp.text[:200]}")
            return None

        data = resp.json()
        plan_key = data.get('key', '(no key)')
        print(f"✅ Created Test Plan: {plan_key} - {original_plan.get('name')}")

        # Wait a moment for the plan to be fully created and indexed
        time.sleep(2)

        # Step 2: Update the plan with test runs and test cases using PUT
        if test_runs or test_cases:
            # Build update payload using ORIGINAL plan data
            # Only include allowed fields for PUT: name, objective, folder, customFields, status, issueLinks, labels, owner
            update_payload = {}

            for field in ["name", "objective", "folder", "customFields", "status", "issueLinks", "labels", "owner"]:
                if field in original_plan:
                    update_payload[field] = original_plan[field]

            # Add test runs as array of key strings (not objects)
            if test_runs:
                update_payload["testRuns"] = [run.get("testRunKey") for run in test_runs if run.get("testRunKey")]

            # Add test cases as array of key strings (not objects)
            if test_cases:
                update_payload["testCases"] = [tc.get("testCaseKey") for tc in test_cases if tc.get("testCaseKey")]

            put_url = f"{base_url}/rest/atm/1.0/testplan/{plan_key}"
            put_resp = session.put(put_url, json=update_payload, timeout=60)

            if put_resp.ok:
                print(f"   🔗 Updated plan with {len(update_payload.get('testRuns', []))} test runs and {len(update_payload.get('testCases', []))} test cases")
            else:
                print(f"   ⚠️ Failed to update plan with links ({put_resp.status_code}): {put_resp.text[:300]}")

        return data
    except RequestException as e:
        print(f"⚠️ Network error while importing plan: {e}")
        return None


def main():
    print(f"🚀 Importing Zephyr test plans into project {TARGET_PROJECT_KEY} @ {TARGET_BASE_URL}")
    session = make_session(TARGET_PAT)

    files = [f for f in os.listdir(EXPORT_DIR) if f.endswith(".json")]
    if not files:
        print(f"⚠️ No JSON plans found in {EXPORT_DIR}")
        return

    for f in files:
        fpath = os.path.join(EXPORT_DIR, f)
        try:
            with open(fpath, "r", encoding="utf-8") as infile:
                plan = json.load(infile)
            import_testplan(session, TARGET_BASE_URL, TARGET_PROJECT_KEY, plan)
            time.sleep(1)
        except Exception as e:
            print(f"⚠️ Error importing {f}: {e}")

    print("🏁 All test plans imported successfully!")


if __name__ == "__main__":
    main()
