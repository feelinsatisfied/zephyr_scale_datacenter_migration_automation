#!/usr/bin/env python3
"""
8_import_testruns_v2.py
---------------------------------
Imports cleaned and remapped Zephyr test runs/cycles into the TARGET Jira Data Center instance.
Loads config and certs automatically from ~/Desktop/zephyr/config and ~/Desktop/zephyr/certs.
"""

import os
import json
import requests
from requests.exceptions import RequestException
from config_loader import TARGET_BASE_URL, TARGET_PAT, TARGET_PROJECT_KEY, CERT_DIR

# ========= CONFIG =========
IN_DIR = os.path.expanduser("~/Desktop/zephyr/exports/runs_clean")
LAZY_FOLDER_MODE = True  # True = skip folder creation to avoid 500 errors
# ==========================

verify_cert = os.path.join(CERT_DIR, "aws_cert_dev.crt")
client_cert = os.path.join(CERT_DIR, "zephyr_cert_test.crt")
client_key = os.path.join(CERT_DIR, "zephyr_pw_key.key")

tls_config = {
    "verify": verify_cert,
    "cert": (client_cert, client_key)
}


def make_session(pat: str) -> requests.Session:
    """Create authenticated HTTPS session with Zephyr target Jira instance."""
    s = requests.Session()
    s.headers.update({
        "Authorization": f"Bearer {pat}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    })
    s.verify = verify_cert
    s.cert = (client_cert, client_key)
    return s


def ensure_folder_exists(session, base_url, project_key, folder_path):
    """Ensure a folder path exists, unless lazy mode is enabled."""
    if not folder_path:
        return None
    if LAZY_FOLDER_MODE:
        print(f"🩹 Skipping folder creation for {folder_path} (lazy mode active).")
        return folder_path
    try:
        parts = [p for p in folder_path.strip("/").split("/") if p]
        current_path = ""
        for part in parts:
            current_path = f"{current_path}/{part}" if current_path else part
            list_url = f"{base_url}/rest/atm/1.0/folder?projectKey={project_key}&maxResults=1000"
            resp = session.get(list_url, timeout=30)
            if not resp.ok:
                print(f"⚠️ Folder list failed ({resp.status_code}): {resp.text[:120]}")
                break
            existing = [f["name"] for f in resp.json().get("values", [])]
            if current_path in existing:
                continue
            payload = {"name": current_path, "projectKey": project_key, "type": "TEST_RUN"}
            create_url = f"{base_url}/rest/atm/1.0/folder"
            resp = session.post(create_url, json=payload, timeout=30)
            if resp.ok:
                print(f"📁 Created folder: {current_path}")
            else:
                print(f"⚠️ Failed to create folder '{current_path}': {resp.status_code} {resp.text[:150]}")
                break
        return folder_path
    except Exception as e:
        print(f"⚠️ Folder creation error for {folder_path}: {e}")
    return None


def create_testrun(session, base_url, project_key, run):
    """Create a new test run in Zephyr Scale DC."""
    try:
        folder_path = run.get("folder")
        ensure_folder_exists(session, base_url, project_key, folder_path)

        payload = {
            "name": run.get("name", "Imported Run"),
            "projectKey": project_key,
            "description": run.get("description", ""),
            "items": run.get("items", []),
            "owner": run.get("owner"),
            "status": run.get("status", "NOT_EXECUTED"),
            # "environment": run.get("environment"),  # Not supported by TARGET API
            "version": run.get("version"),
        }

        # Only include folder if lazy mode is off and folder was created
        if not LAZY_FOLDER_MODE and folder_path:
            payload["folder"] = folder_path

        create_url = f"{base_url}/rest/atm/1.0/testrun"
        resp = session.post(create_url, json=payload, timeout=600)  # 10 minutes for large test runs
        if resp.ok:
            data = resp.json()
            print(f"✅ Created Test Run: {data.get('key', '(no key)')} - {run.get('name')}")
            return data
        else:
            print(f"❌ Failed to create test run: {resp.status_code} {resp.text[:300]}")
            return None

    except RequestException as e:
        print(f"⚠️ Network error while creating test run: {e}")
        return None


def upload_testresults(session, base_url, testrun_key, results):
    """Upload test results to an existing test run."""
    if not results:
        return
    url = f"{base_url}/rest/atm/1.0/testrun/{testrun_key}/testresults"
    resp = session.post(url, json=results, timeout=60)
    if resp.ok:
        print(f"📈 Uploaded {len(results)} results to {testrun_key}")
    else:
        print(f"⚠️ Failed to upload results: {resp.status_code} {resp.text[:200]}")


def main():
    print(f"▶ Importing test runs from {IN_DIR}")
    session = make_session(TARGET_PAT)

    run_files = [f for f in os.listdir(IN_DIR) if f.endswith(".json")]
    if not run_files:
        print(f"⚠️ No test runs found in {IN_DIR}")
        return

    for rf in run_files:
        path = os.path.join(IN_DIR, rf)
        try:
            with open(path, "r", encoding="utf-8") as f:
                run = json.load(f)
            created = create_testrun(session, TARGET_BASE_URL, TARGET_PROJECT_KEY, run)
            if created and "results" in run:
                upload_testresults(session, TARGET_BASE_URL, created.get("key"), run["results"])
        except Exception as e:
            print(f"⚠️ Error processing {rf}: {e}")

    print("✅ Import completed successfully.")


if __name__ == "__main__":
    main()
