#!/usr/bin/env python3
"""
config_loader.py
Centralized configuration and TLS setup for Zephyr Scale migration scripts.
"""

import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ======== PATH SETUP ========
BASE_PATH = os.path.expanduser("~/Desktop/zephyr")
CONFIG_DIR = os.path.join(BASE_PATH, "config")
CERT_DIR = os.path.join(BASE_PATH, "certs")
EXPORT_DIR = os.path.join(BASE_PATH, "exports")

# Ensure directories exist
os.makedirs(EXPORT_DIR, exist_ok=True)

# ======== CONFIG FILES ========
def load_text(path, fallback=None):
    """Safely read a single-line text config file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        print(f"⚠️  Missing config file: {path}")
        return fallback

SOURCE_BASE_URL = load_text(os.path.join(CONFIG_DIR, "source_base_url.txt"))
SOURCE_PAT = load_text(os.path.join(CONFIG_DIR, "source_pat.txt"))
SOURCE_PROJECT_KEY = load_text(os.path.join(CONFIG_DIR, "source_proj_key.txt"))

TARGET_BASE_URL = load_text(os.path.join(CONFIG_DIR, "target_base_url.txt"))
TARGET_PAT = load_text(os.path.join(CONFIG_DIR, "target_pat.txt"))
TARGET_PROJECT_KEY = load_text(os.path.join(CONFIG_DIR, "target_proj_key.txt"))

# ======== CERTIFICATES ========
AWS_CERT = os.path.join(CERT_DIR, "aws_cert_dev.crt")
CLIENT_CERT = os.path.join(CERT_DIR, "zephyr_cert_test.crt")
CLIENT_KEY = os.path.join(CERT_DIR, "zephyr_pw_key.key")

for f in [AWS_CERT, CLIENT_CERT, CLIENT_KEY]:
    if not os.path.exists(f):
        print(f"⚠️  Missing certificate: {f}")

TLS_CONFIG = {
    "verify": AWS_CERT,
    "cert": (CLIENT_CERT, CLIENT_KEY)
}

# ======== SESSION CREATOR ========
def create_session(pat: str):
    """Create a resilient requests.Session configured for Jira + Zephyr."""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {pat}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    })

    retry_strategy = Retry(
        total=5,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)

    return session

# ======== TEST PRINT ========
if __name__ == "__main__":
    print("🌐 Loaded config:")
    print(f"  SOURCE_BASE_URL = {SOURCE_BASE_URL}")
    print(f"  SOURCE_PROJECT_KEY = {SOURCE_PROJECT_KEY}")
    print(f"  TARGET_BASE_URL = {TARGET_BASE_URL}")
    print(f"  TARGET_PROJECT_KEY = {TARGET_PROJECT_KEY}")
    print(f"  Certs loaded: {os.path.exists(AWS_CERT)}, {os.path.exists(CLIENT_CERT)}, {os.path.exists(CLIENT_KEY)}")
