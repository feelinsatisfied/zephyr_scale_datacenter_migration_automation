# Zephyr Scale Migration Tool

A Python toolkit for migrating Zephyr Scale test data between Jira Data Center instances while preserving all relationships between test cases, test runs, and test plans.

## The Problem

When you export and import Zephyr Scale data between Jira instances, all entities get new keys. Test cases that were `PROJ-T123` become `TARGET-T456`, breaking all references in test runs and test plans. You end up with imported data that looks complete but has broken relationships throughout.

## The Solution

This tool uses content-based signature matching to build key mappings after import. Since keys change but content stays the same, we can match entities by their attributes and remap all references automatically.

**Test cases** are matched by: name, description/objective, and first two test steps 

**Test runs** are matched by: name, description, environment, version, and item count

## How It Works

The migration runs in three phases:

### Phase 1: Test Cases
1. Export test cases from source instance
2. Clean data (remove IDs, timestamps that cause conflicts)
3. Import to target instance
4. Build key mapping by comparing source export with target instance

### Phase 2: Test Runs
1. Export test runs from source
2. Remap test case references using Phase 1 mapping
3. Import to target
4. Build test run key mapping

### Phase 3: Test Plans
1. Export test plans from source
2. Remap both test case and test run references
3. Import to target

## Prerequisites

- Python 3.6+
- `requests` library
- Personal Access Tokens for both Jira instances
- Target project must exist with Zephyr Scale structure in place:
  - Folder hierarchy
  - Custom fields
  - Environments and versions

## Setup

1. Clone the repository to `~/Desktop/zephyr`:
   ```bash
   git clone https://github.com/feelinsatisfied/zephyr_scale_datacenter_migration_automation.git ~/Desktop/zephyr
   ```

2. Install dependencies:
   ```bash
   pip install requests
   ```

3. Create config files (copy from samples and edit):
   ```bash
   cd config
   cp SAMPLE_source_base_url.txt source_base_url.txt
   cp SAMPLE_source_pat.txt source_pat.txt
   cp SAMPLE_source_proj_key.txt source_proj_key.txt
   cp SAMPLE_target_base_url.txt target_base_url.txt
   cp SAMPLE_target_pat.txt target_pat.txt
   cp SAMPLE_target_proj_key.txt target_proj_key.txt
   ```

4. Edit each file with your actual values (one value per file, no trailing newlines)

5. If your environment requires TLS certificates, add them to `certs/`:
   - `aws_cert_dev.crt` - CA certificate
   - `zephyr_cert_test.crt` - Client certificate
   - `zephyr_pw_key.key` - Client private key

## Usage

Run the migration orchestrator:

```bash
cd ~/Desktop/zephyr
python 0_run_zephyr_migration_orchestrator_v2.py
```

The orchestrator runs each step in sequence. If a step fails, you can fix the issue and re-run—completed steps will be skipped.

### Manual Step Execution

You can also run individual scripts from the `scripts/` directory:

| Step | Script | Description |
|------|--------|-------------|
| 1 | `1_export_zephyr_scale_all_v2.py` | Export all data from source |
| 2 | `2_clean_up_zephyr_scale_all_v5.py` | Clean export for import |
| 2.5 | `2.5_build_testcase_mapping.py` | Build test case key mapping |
| 3 | `3_import_zephyr_scale_all_v3.py` | Import test cases to target |
| 5 | `5_export_testruns_from_full_export.py` | Extract test runs |
| 6 | `6_remap_testrun_ids_v3.py` | Remap test case references |
| 7 | `7_clean_testruns_for_import.py` | Clean test runs |
| 8 | `8_import_testruns.py` | Import test runs |
| 8.5 | `8.5_build_testrun_mapping.py` | Build test run key mapping |
| 9 | `9_export_testplans.py` | Export test plans |
| 10 | `10_clean_and_map_testplans_v3.py` | Remap test plan references |
| 11 | `11_import_testplans.py` | Import test plans |

## Directory Structure

```
~/Desktop/zephyr/
├── 0_run_zephyr_migration_orchestrator_v2.py  # Main entry point
├── config/                                     # Connection settings
│   ├── source_base_url.txt
│   ├── source_pat.txt
│   ├── source_proj_key.txt
│   ├── target_base_url.txt
│   ├── target_pat.txt
│   └── target_proj_key.txt
├── certs/                                      # TLS certificates (optional)
├── exports/                                    # Generated data files
│   ├── zephyr_scale_full_export.json
│   ├── testcase_key_mapping.json
│   ├── testrun_key_mapping.json
│   └── ...
├── logs/                                       # Execution logs
└── scripts/                                    # Migration step scripts
```

## Limitations

- **Manual structure setup required**: You must recreate folders, custom fields, environments, and versions in the target before running
- **Content-based matching**: Assumes test case names/descriptions are reasonably unique. Identical test cases may not match correctly
- **Data Center only**: Designed for Jira Data Center. Cloud API endpoints differ
- **No attachment handling**: Attachments must be migrated separately

## Safety

- All source instance operations are **read-only** (GET requests only)
- Your source data is never modified
- TLS/SSL certificate validation supported
- Credentials stored in local files (never committed to repo)

## Documentation

- [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) - Detailed migration walkthrough
- [FIELD_PRUNING_EXPLAINED.md](FIELD_PRUNING_EXPLAINED.md) - Data cleaning details
- [SOURCE_SAFETY_VERIFICATION.md](SOURCE_SAFETY_VERIFICATION.md) - Security audit
- [UPGRADE_FROM_V1.md](UPGRADE_FROM_V1.md) - Upgrading from earlier versions

## Contributing

Issues and pull requests are welcome. Please open an issue first to discuss significant changes.

## License

MIT License - see [LICENSE](LICENSE) for details.
