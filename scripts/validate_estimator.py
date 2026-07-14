#!/usr/bin/env python3
"""
Validation: compare estimator's predicted pipeline duration
against observed GitLab durations on a held-out sample.
"""
import requests, yaml, json, time, urllib.parse, argparse, statistics
from pathlib import Path

GITLAB_API = "https://gitlab.com/api/v4"

def get_headers(token):
    h = {"Accept": "application/json"}
    if token: h["PRIVATE-TOKEN"] = token
    return h

def get_ci_yaml(project_id, token):
    url = f"{GITLAB_API}/projects/{project_id}/repository/files/{urllib.parse.quote('.gitlab-ci.yml', safe='')}/raw"
    r = requests.get(url, headers=get_headers(token), params={"ref": "HEAD"}, timeout=30)
    return r.text if r.status_code == 200 else None

# In validate_estimator.py, replace the get_avg_duration function with:
def get_avg_duration(project_id, token, n=10):
    url = f"{GITLAB_API}/projects/{project_id}/pipelines"
    r = requests.get(url, headers=get_headers(token),
                     params={"per_page": n, "status": "success"}, timeout=30)
    if r.status_code != 200:
        return None, f"HTTP {r.status_code}"
    pipelines = r.json()
    if not pipelines:
        return None, "no successful pipelines"
    durations = [p["duration"] for p in pipelines if p.get("duration")]
    if not durations:
        return None, f"{len(pipelines)} pipelines, all with null duration"
    return statistics.mean(durations), None

def estimate_duration_minutes(content):
    """Same logic as generate_dataset_stats.py — must stay in sync."""
    try:
        data = yaml.safe_load(content)
        if not isinstance(data, dict): return None
    except: return None
    reserved = {"stages","variables","image","services","before_script",
                "after_script","cache","include","default","workflow",
                "pages",".pre",".post"}
    total = 0.0
    for key, cfg in data.items():
        if key in reserved or key.startswith("."): continue
        if not isinstance(cfg, dict): continue
        scripts = []
        for k in ["before_script","script","after_script"]:
            s = cfg.get(k, [])
            if isinstance(s, list): scripts.extend(s)
            elif isinstance(s, str): scripts.append(s)
        text = " ".join(str(s) for s in scripts).lower()
        d = 1.0
        if any(k in text for k in ["apt-get","apk add","yum install"]): d += 3.0
        if any(k in text for k in ["npm install","npm ci","yarn install"]): d += 2.5
        if any(k in text for k in ["pip install","poetry install","conda install"]): d += 2.0
        if any(k in text for k in ["docker build","buildah","kaniko"]): d += 5.0
        if any(k in text for k in ["make","cmake","cargo build","go build","mvn","gradle"]): d += 8.0
        if any(k in text for k in ["test","pytest","jest","rspec","phpunit"]): d += 4.0
        if any(k in text for k in ["deploy","kubectl","helm","terraform"]): d += 3.0
        if "echo" in text and d == 1.0: d = 0.5
        total += min(d, 20.0)
    return total if total > 0 else None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--token", required=True, help="GitLab personal access token")
    ap.add_argument("--dataset", default="dataset/greenpipe_dataset.json")
    ap.add_argument("--target", type=int, default=20, help="Target held-out sample size")
    ap.add_argument("--output", default="validation_results.csv")
    args = ap.parse_args()

    with open(args.dataset) as f:
        projects = json.load(f)

    print(f"Trying projects from dataset until {args.target} have observed durations...")
    results = []
    for proj in projects:
        if len(results) >= args.target:
            break
        pid = proj["project_id"]
        path = proj.get("project_path", "?")
        observed, reason = get_avg_duration(pid, args.token)
        time.sleep(0.4)
        if observed is None:
            print(f"  skip {path}: {reason}")
            continue
        time.sleep(0.4)
        if observed is None or observed < 10:  # skip trivial pipelines
            continue
        content = get_ci_yaml(pid, args.token)
        time.sleep(0.4)
        if not content:
            continue
        predicted_min = estimate_duration_minutes(content)
        if predicted_min is None:
            continue
        predicted_sec = predicted_min * 60
        ape = abs(predicted_sec - observed) / observed * 100
        results.append({
            "project": path,
            "predicted_sec": round(predicted_sec, 1),
            "observed_sec": round(observed, 1),
            "abs_pct_error": round(ape, 1),
        })
        print(f"  {len(results):2d}. {path:<50} pred={predicted_sec:6.0f}s  obs={observed:6.0f}s  APE={ape:.1f}%")

    if not results:
        print("No usable samples — public projects rarely expose durations. Try passing your own token with API scope."); return

    mape = statistics.mean(r["abs_pct_error"] for r in results)
    median_ape = statistics.median(r["abs_pct_error"] for r in results)
    print(f"\n=== Validation Summary ===")
    print(f"n = {len(results)}")
    print(f"MAPE   = {mape:.1f}%")
    print(f"Median APE = {median_ape:.1f}%")

    with open(args.output, "w") as f:
        f.write("project,predicted_sec,observed_sec,abs_pct_error\n")
        for r in results:
            f.write(f"{r['project']},{r['predicted_sec']},{r['observed_sec']},{r['abs_pct_error']}\n")
        f.write(f"\nMAPE,{mape:.1f}\n")
        f.write(f"MedianAPE,{median_ape:.1f}\n")
    print(f"Saved -> {args.output}")

if __name__ == "__main__":
    main()
