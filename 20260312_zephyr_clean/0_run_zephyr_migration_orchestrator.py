# 0_run_zephyr_migration_orchestrator.py
import os
import sys
import json
import time
import subprocess
from pathlib import Path
from typing import Optional, Dict, List

# ──────────────────────────────────────────────────────────────────────────────
# Locations
# ──────────────────────────────────────────────────────────────────────────────
DESKTOP = Path.home() / "Desktop"
ROOT    = DESKTOP / "zephyr"
CONFIG  = ROOT / "config"
CERTS   = ROOT / "certs"
EXPORTS = ROOT / "exports"
LOGS    = ROOT / "logs"
SCRIPTS_DIR = ROOT / "scripts"

SCRIPTS = {
    1:  "1_export_zephyr_scale_all_v2.py",
    2:  "2_clean_up_zephyr_scale_all_v5.py",
    3:  "3_import_zephyr_scale_all_v3.py",
    4:  "4_export_target_testcases.py",
    5:  "5_export_testrun_by_key.py",
    6:  "6_remap_testrun_ids.py",
    7:  "7_clean_testruns_for_import.py",
    8:  "8_import_testruns.py",
    9:  "9_export_testplans.py",
    10: "10_clean_and_map_testplans.py",
    11: "11_import_testplans.py",
}

OUT = {
    "cases_source_raw":   EXPORTS / "testcases_source" / "testcases_source.json",
    "cases_source_clean": EXPORTS / "testcases_source" / "testcases_source_clean.json",
    "cases_target_raw":   EXPORTS / "testcases_target" / "testcases_target.json",
    "runs_source_dir":    EXPORTS / "testruns_source",
    "runs_remap_dir":     EXPORTS / "testruns_remapped",
    "plans_source_dir":   EXPORTS / "testplans_source",
}

RUN_KEYS_FILE  = CONFIG / "source_run_keys.txt"
PLAN_KEYS_FILE = CONFIG / "source_plan_keys.txt"

LOGS.mkdir(parents=True, exist_ok=True)
EXPORTS.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOGS / "migration_log.txt"

# ──────────────────────────────────────────────────────────────────────────────
# Helper Functions
# ──────────────────────────────────────────────────────────────────────────────
def log(msg: str):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def read_txt(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip() if path.exists() else ""

def load_config() -> Dict[str, str]:
    cfg = {
        "SOURCE_BASE_URL": read_txt(CONFIG / "source_base_url.txt"),
        "TARGET_BASE_URL": read_txt(CONFIG / "target_base_url.txt"),
        "SOURCE_PAT":      read_txt(CONFIG / "source_pat.txt"),
        "TARGET_PAT":      read_txt(CONFIG / "target_pat.txt"),
        "SOURCE_PROJECT":  read_txt(CONFIG / "source_proj_key.txt"),
        "TARGET_PROJECT":  read_txt(CONFIG / "target_proj_key.txt"),
        "VERIFY_CA":       str(CERTS / "aws_cert_dev.crt"),
        "CLIENT_CERT":     str(CERTS / "zephyr_cert_test.crt"),
        "CLIENT_KEY":      str(CERTS / "zephyr_pw_key.key"),
    }
    missing = [k for k, v in cfg.items() if not v]
    if missing:
        log(f"⚠️ Missing values for: {', '.join(missing)}")
    return cfg

def run_step(step_num: int, label: str, skip_if: Optional[List[Path]] = None) -> bool:
    script = SCRIPTS_DIR / SCRIPTS.get(step_num, "")
    if not script.exists():
        log(f"❌ Step {step_num} '{label}': script not found at {script}")
        return False

    if skip_if and all(p.exists() and (p.stat().st_size > 0 if p.is_file() else list(p.glob('*.json'))) for p in skip_if):
        log(f"⏭️ Step {step_num} '{label}' skipped (outputs already present).")
        return True

    log(f"▶️ Step {step_num}: {label}")
    proc = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
    if proc.returncode != 0:
        log(f"❌ Step {step_num} failed.\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
        return False

    if proc.stdout.strip():
        log(f"ℹ️ Output:\n{proc.stdout}")
    if proc.stderr.strip():
        log(f"⚠️ Warnings:\n{proc.stderr}")
    log(f"✅ Step {step_num} completed: {label}")
    return True

# ──────────────────────────────────────────────────────────────────────────────
# Main Orchestration
# ──────────────────────────────────────────────────────────────────────────────
def main():
    print("\n╔══════════════════════════════════════════════════════════════╗")
    print("║     Zephyr Scale DC Migration Orchestrator (Steps 1–12)     ║")
    print("╚══════════════════════════════════════════════════════════════╝\n")

    cfg = load_config()

    log("📁 Paths in use:")
    log(f"  CONFIG  → {CONFIG}")
    log(f"  CERTS   → {CERTS}")
    log(f"  EXPORTS → {EXPORTS}")
    log(f"  SCRIPTS → {SCRIPTS_DIR}")
    log(f"  LOGS    → {LOGS}")
    log(f"  SOURCE_BASE_URL → {cfg['SOURCE_BASE_URL']}")
    log(f"  TARGET_BASE_URL → {cfg['TARGET_BASE_URL']}")

    steps = [
        (1,  "Export test cases from SOURCE",        [OUT["cases_source_raw"]]),
        (2,  "Clean test cases",                     [OUT["cases_source_clean"]]),
        (3,  "Import test cases into TARGET",        [OUT["cases_target_raw"]]),
        (4,  "Export test cases from TARGET",        [OUT["cases_target_raw"]]),
        (5,  "Export test runs from SOURCE",         [OUT["runs_source_dir"]]),
        (6,  "Remap test run IDs",                   [OUT["runs_remap_dir"]]),
        (7,  "Clean test runs for import",           [OUT["runs_remap_dir"]]),
        (8,  "Import test runs into TARGET",         []),
        (9,  "Export test plans from SOURCE",        [OUT["plans_source_dir"]]),
        (10, "Clean and map test plans",             []),
        (11, "Import test plans into TARGET",        []),
        (12, "Validate migration results",           [])
    ]

    for step_num, label, skip_if in steps:
        if not run_step(step_num, label, skip_if):
            log(f"❌ Migration halted at Step {step_num}")
            break
        time.sleep(1)

    log("🎉 Migration orchestration complete.")

# ──────────────────────────────────────────────────────────────
# Entry Point
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()
