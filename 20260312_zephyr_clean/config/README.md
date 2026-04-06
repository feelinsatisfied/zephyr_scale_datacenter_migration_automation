# Config Directory

This directory contains configuration files for connecting to your Jira instances.

## Required Files

Create the following text files (one value per file, no trailing newlines):

| File | Description | Example |
|------|-------------|---------|
| `source_base_url.txt` | Source Jira instance URL | `https://source-jira.example.com` |
| `source_pat.txt` | Source instance Personal Access Token | `ATATT3xFfGF0...` |
| `source_proj_key.txt` | Source project key | `SRCPROJ` |
| `target_base_url.txt` | Target Jira instance URL | `https://target-jira.example.com` |
| `target_pat.txt` | Target instance Personal Access Token | `ATATT3xFfGF0...` |
| `target_proj_key.txt` | Target project key | `TGTPROJ` |

## Security Note

These files contain sensitive credentials. They are excluded from version control via `.gitignore`.

**Never commit these files to a public repository.**
