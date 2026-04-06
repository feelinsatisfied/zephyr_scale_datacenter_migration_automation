# Exports Directory

This directory contains exported data and mapping files generated during migration.

## Generated Subdirectories

The migration scripts will create the following:

| Directory/File | Created By | Description |
|----------------|------------|-------------|
| `zephyr_scale_full_export.json` | Step 1 | Full export from source instance |
| `zephyr_scale_full_clean.json` | Step 2 | Cleaned export ready for import |
| `testcase_key_mapping.json` | Step 2.5 | Source→Target test case key mapping |
| `testruns_source/` | Step 5 | Individual test run exports |
| `testruns_remapped/` | Step 6 | Test runs with updated key references |
| `runs_clean/` | Step 7 | Cleaned test runs ready for import |
| `testrun_key_mapping.json` | Step 8.5 | Source→Target test run key mapping |
| `testplans_source/` | Step 9 | Test plan exports from source |
| `testplans_clean/` | Step 10 | Test plans with updated references |

## Note

All export files are excluded from version control via `.gitignore`.

These files contain project-specific data and should not be committed.
