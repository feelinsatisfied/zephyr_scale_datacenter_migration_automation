# 0_run_zephyr_migration_orchestrator_v2.py
import os
import sys
import json
import time
import subprocess
import argparse
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
    1:    "1_export_zephyr_scale_all_v2.py",
    2:    "2_clean_up_zephyr_scale_all_v5.py",
    3:    "3_import_zephyr_scale_all_v3.py",
    2.5:  "2.5_build_testcase_mapping.py",          # NEW: Build test case mapping
    5:    "5_export_testruns_from_full_export.py",  # FIXED: Extract runs from full export
    6:    "6_remap_testrun_ids_v3.py",              # UPDATED: Use new mapping
    7:    "7_clean_testruns_for_import.py",
    8:    "8_import_testruns.py",
    8.5:  "8.5_build_testrun_mapping.py",           # NEW: Build test run mapping
    9:    "9_export_testplans.py",
    10:   "10_clean_and_map_testplans_v3.py",       # UPDATED: Use both mappings
    11:   "11_import_testplans.py",
}

OUT = {
    "full_export":            EXPORTS / "zephyr_scale_full_export.json",  # FIXED: actual step 1 output
    "full_export_clean":      EXPORTS / "zephyr_scale_full_clean.json",   # FIXED: actual step 2 output
    "testcase_key_mapping":   EXPORTS / "testcase_key_mapping.json",
    "runs_source_dir":        EXPORTS / "testruns_source",
    "runs_remap_dir":         EXPORTS / "testruns_remapped",
    "runs_clean_dir":         EXPORTS / "runs_clean",
    "testrun_key_mapping":    EXPORTS / "testrun_key_mapping.json",
    "plans_source_dir":       EXPORTS / "plans_export",  # FIXED: actual step 9 output directory
    "plans_clean_dir":        EXPORTS / "testplans_clean",
}

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

def run_step(step_num: float, label: str, skip_if: Optional[List[Path]] = None) -> bool:
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
    print("║   Zephyr Scale DC Migration Orchestrator v2 (Enhanced)     ║")
    print("║        with Automated ID Mapping & Relationship Tracking     ║")
    print("╚══════════════════════════════════════════════════════════════╝\n")

    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='Zephyr Scale Migration Orchestrator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python 0_run_zephyr_migration_orchestrator_v2.py           # Run from beginning
  python 0_run_zephyr_migration_orchestrator_v2.py --resume 9   # Resume from step 9
  python 0_run_zephyr_migration_orchestrator_v2.py --resume 2.5 # Resume from step 2.5
        """
    )
    parser.add_argument(
        '--resume',
        type=float,
        metavar='STEP',
        help='Resume from specific step number (e.g., 9 or 2.5)'
    )

    args = parser.parse_args()
    start_from = args.resume if args.resume else 1

    if start_from > 1:
        print(f"🔄 Resuming from step {start_from}\n")

    cfg = load_config()

    log("📁 Paths in use:")
    log(f"  CONFIG  → {CONFIG}")
    log(f"  CERTS   → {CERTS}")
    log(f"  EXPORTS → {EXPORTS}")
    log(f"  SCRIPTS → {SCRIPTS_DIR}")
    log(f"  LOGS    → {LOGS}")
    log(f"  SOURCE_BASE_URL → {cfg['SOURCE_BASE_URL']}")
    log(f"  TARGET_BASE_URL → {cfg['TARGET_BASE_URL']}")

    log("\n📋 Migration Plan:")
    log("  Phase 1: Test Cases (Export → Clean → Import → Build Mapping)")
    log("  Phase 2: Test Runs (Export → Remap IDs → Clean → Import → Build Mapping)")
    log("  Phase 3: Test Plans (Export → Remap IDs → Clean → Import)")
    log("")

    steps = [
        # ═══════════════════════════════════════════════════════
        # PHASE 1: TEST CASES
        # ═══════════════════════════════════════════════════════
        (1,   "Export test cases from SOURCE",           [OUT["full_export"]]),
        (2,   "Clean test cases for import",             [OUT["full_export_clean"]]),
        (3,   "Import test cases into TARGET",           [OUT["testcase_key_mapping"]]),  # Skip if mapping exists
        (2.5, "🔗 Build test case key mapping",          [OUT["testcase_key_mapping"]]),

        # ═══════════════════════════════════════════════════════
        # PHASE 2: TEST RUNS
        # ═══════════════════════════════════════════════════════
        (5,   "Export test runs from SOURCE",            [OUT["runs_source_dir"]]),
        (6,   "🔄 Remap test run test case keys",        [OUT["runs_remap_dir"]]),
        (7,   "Clean test runs for import",              [OUT["runs_clean_dir"]]),
        (8,   "Import test runs into TARGET",            [OUT["testrun_key_mapping"]]),  # Skip if mapping exists
        (8.5, "🔗 Build test run key mapping",           [OUT["testrun_key_mapping"]]),

        # ═══════════════════════════════════════════════════════
        # PHASE 3: TEST PLANS
        # ═══════════════════════════════════════════════════════
        # Step 9 skipped - test plans already exported in step 1
        (10,  "🔄 Remap test plan references",           [OUT["plans_clean_dir"]]),
        (11,  "Import test plans into TARGET",           None),  # Always run - imports to TARGET
    ]

    for step_num, label, skip_if in steps:
        # Skip steps before start_from
        if step_num < start_from:
            continue
        if not run_step(step_num, label, skip_if):
            log(f"❌ Migration halted at Step {step_num}")
            log(f"   Please review the error above and re-run the orchestrator.")
            break

        # Add extra delay before step 11 to ensure test runs are fully indexed
        if step_num == 10:
            log("⏳ Waiting 5 seconds for test runs to be fully indexed before linking to plans...")
            time.sleep(5)
        else:
            time.sleep(1)
    else:
        # Only runs if no break occurred
        log("")
        log("🎉 Migration orchestration complete!")
        log("")
        log("📊 Generated Mapping Files:")
        if OUT["testcase_key_mapping"].exists():
            log(f"  ✅ Test Case Mapping: {OUT['testcase_key_mapping']}")
        if OUT["testrun_key_mapping"].exists():
            log(f"  ✅ Test Run Mapping: {OUT['testrun_key_mapping']}")
        log("")
        log("✅ All test cases, runs, and plans have been migrated with preserved links!")

# ──────────────────────────────────────────────────────────────
# Entry Point
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()