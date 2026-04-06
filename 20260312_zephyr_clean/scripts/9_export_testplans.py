#!/usr/bin/env python3
"""
9_export_testplans_v2.py
--------------------------------
Exports Zephyr Scale test plans (and optionally a single plan) from the SOURCE Jira Data Center instance.

Configuration and credentials are read automatically from:
~/Desktop/zephyr/config/source_base_url.txt
~/Desktop/zephyr/config/source_pat.txt
~/Desktop/zephyr/config/source_proj_key.txt
"""

import os
import json
import time
import requests

# ========= CONFIG PATHS =========
CONFIG_DIR = os.path.expanduser("~/Desktop/zephyr/config")
EXPORT_DIR = os.path.expanduser("~/Desktop/zephyr/exports/plans_export")

# ========= LOAD CONFIG =========
def read_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()

SOURCE_BASE_URL = read_file(os.path.join(CONFIG_DIR, "source_base_url.txt"))
SOURCE_PAT = read_file(os.path.join(CONFIG_DIR, "source_pat.txt"))
SOURCE_PROJECT_KEY = read_file(os.path.join(CONFIG_DIR, "source_proj_key.txt"))

os.makedirs(EXPORT_DIR, exist_ok=True)

# ========= SESSION SETUP =========
def make_source_session(pat: str) -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "Authorization": f"Bearer {pat}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    })
    return s


# ========= RETRY WRAPPER =========
def get_with_retry(session, url, params=None, tries=5):
    """GET with exponential backoff retries."""
    for attempt in range(tries):
        resp = session.get(url, params=params, timeout=60)
        if resp.ok:
            return resp
        print(f"⚠️ Retry {attempt+1}/{tries}: {resp.status_code} {resp.text[:150]}")
        time.sleep(2 ** attempt)
    resp.raise_for_status()


# ========= CORE EXPORT FUNCTIONS =========
def export_testplan(session, base_url, plan_key):
    """Export a single test plan with all its linked runs."""
    url = f"{base_url}/rest/atm/1.0/testplan/{plan_key}"
    resp = get_with_retry(session, url)
    data = resp.json()

    path = os.path.join(EXPORT_DIR, f"testplan_{plan_key}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"💾 Exported test plan {plan_key}")

    return data


def export_all_testplans(session, base_url, project_key):
    """List all test plans in the project (paginated) and export each one."""
    all_plans = []
    start_at = 0
    page_size = 100

    while True:
        url = f"{base_url}/rest/atm/1.0/testplan"
        params = {"projectKey": project_key, "startAt": start_at, "maxResults": page_size}
        resp = get_with_retry(session, url, params)
        data = resp.json()

        values = data.get("values", data if isinstance(data, list) else [])
        if not values:
            break

        for plan in values:
            key = plan.get("key")
            if not key:
                continue
            full = export_testplan(session, base_url, key)
            all_plans.append(full)

        if len(values) < page_size:
            break
        start_at += page_size

    combined_path = os.path.join(EXPORT_DIR, "testplans_all.json")
    with open(combined_path, "w", encoding="utf-8") as f:
        json.dump(all_plans, f, indent=2, ensure_ascii=False)
    print(f"✅ Exported {len(all_plans)} test plans total → {combined_path}")


# ========= MAIN =========
def main():
    print(f"🚀 Exporting Zephyr test plans from project {SOURCE_PROJECT_KEY} @ {SOURCE_BASE_URL}")
    session = make_source_session(SOURCE_PAT)

    # Export all test plans (skip interactive prompt when run by orchestrator)
    export_all_testplans(session, SOURCE_BASE_URL, SOURCE_PROJECT_KEY)

    print(f"🏁 Completed test plan export → {EXPORT_DIR}")


if __name__ == "__main__":
    main()
