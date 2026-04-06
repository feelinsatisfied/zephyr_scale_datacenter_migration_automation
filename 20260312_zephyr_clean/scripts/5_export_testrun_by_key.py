#!/usr/bin/env python3
import os, sys, json, time, argparse
import requests

def make_source_session(pat: str) -> requests.Session:
    s = requests.Session()
    # If your source needs Basic instead, replace with:
    # from base64 import b64encode
    # s.headers["Authorization"] = "Basic " + b64encode(f"{USER}:{pat}".encode()).decode()
    s.headers.update({
        "Authorization": f"Bearer {pat}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    })
    return s

def get_with_retry(session: requests.Session, url: str, params=None, tries=5, timeout=60):
    for attempt in range(tries):
        resp = session.get(url, params=params, timeout=timeout)
        if resp.ok:
            return resp
        time.sleep(2 ** attempt)
    resp.raise_for_status()
    return resp

def export_testrun(session: requests.Session, base_url: str, run_key: str) -> dict:
    url = f"{base_url}/rest/atm/1.0/testrun/{run_key}"
    resp = get_with_retry(session, url)
    return resp.json()

def export_testrun_results(session: requests.Session, base_url: str, run_key: str, page_size=200) -> list:
    """Paginates results if server supports startAt/maxResults; otherwise returns list once."""
    all_results = []
    start_at = 0
    while True:
        url = f"{base_url}/rest/atm/1.0/testrun/{run_key}/testresults"
        params = {"startAt": start_at, "maxResults": page_size}
        resp = get_with_retry(session, url, params=params)
        data = resp.json()
        # Some DC returns a plain list; some returns {values:[...]}
        values = data.get("values", data if isinstance(data, list) else [])
        all_results.extend(values)
        if isinstance(data, list) or len(values) < page_size:
            break
        start_at += page_size
    return all_results

def main():
    ap = argparse.ArgumentParser(description="Export a single testrun (+results) from SOURCE instance by key.")
    ap.add_argument("--base-url", default=os.getenv("SOURCE_BASE_URL", "https://source.com/jira"))
    ap.add_argument("--pat", default=os.getenv("SOURCE_PAT", os.getenv("JIRA_PAT", "PAT_Here")))
    ap.add_argument("--run-key", required=True, help="e.g. STD-R123")
    ap.add_argument("--out-dir", default="runs_export")
    ap.add_argument("--with-results", action="store_true", help="Fetch /testresults and produce merged file")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    session = make_source_session(args.pat)

    print(f"➡️  Exporting run {args.run_key} from {args.base_url} ...")
    run = export_testrun(session, args.base_url, args.run_key)
    run_path = os.path.join(args.out_dir, f"run_{args.run_key}.json")
    with open(run_path, "w", encoding="utf-8") as f:
        json.dump(run, f, indent=2, ensure_ascii=False)
    print(f"💾 Saved testrun → {run_path}")

    if args.with_results:
        results = export_testrun_results(session, args.base_url, args.run_key)
        res_path = os.path.join(args.out_dir, f"run_{args.run_key}_results.json")
        with open(res_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"💾 Saved results → {res_path}")

        merged = dict(run)
        merged["results"] = results
        merged_path = os.path.join(args.out_dir, f"run_{args.run_key}_merged.json")
        with open(merged_path, "w", encoding="utf-8") as f:
            json.dump(merged, f, indent=2, ensure_ascii=False)
        print(f"💾 Saved merged → {merged_path}")

if __name__ == "__main__":
    main()
