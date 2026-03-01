#!/usr/bin/env python3
"""
Reads the collected dataset and generates:
1. dataset_stats.yml - Summary stats for embedding in agent prompt
2. dataset_benchmarks.json - Full benchmarks for the agent to read at runtime
3. batch_analysis_results.csv - Before/after SCI for each pipeline (research output)
"""

import json
import yaml
import os
import sys
from pathlib import Path
from collections import Counter

def load_dataset(dataset_dir):
    """Load the collected dataset."""
    json_path = Path(dataset_dir) / "greenpipe_dataset.json"
    if not json_path.exists():
        print(f"ERROR: {json_path} not found. Run collect_gitlab_ci_dataset.py first.")
        sys.exit(1)
    with open(json_path) as f:
        return json.load(f)

def calculate_sci_for_yaml(content):
    """
    Static SCI estimation for a .gitlab-ci.yml file.
    Uses the same logic the agent uses, but automated.
    """
    TDP_W = 7       # Watts per job (shared runner)
    PUE = 1.1
    CARBON_INTENSITY = 400  # gCO2e/kWh global average
    EMBODIED_RATE = 34.25   # gCO2e per hour of runner use

    try:
        data = yaml.safe_load(content)
        if not isinstance(data, dict):
            return None
    except:
        return None

    reserved = {
        "stages", "variables", "image", "services", "before_script",
        "after_script", "cache", "include", "default", "workflow",
        "pages", ".pre", ".post",
    }

    # Estimate duration per job type
    def estimate_job_minutes(job_name, job_config):
        if not isinstance(job_config, dict):
            return 1
        scripts = []
        for key in ["before_script", "script", "after_script"]:
            s = job_config.get(key, [])
            if isinstance(s, list):
                scripts.extend(s)
            elif isinstance(s, str):
                scripts.append(s)
        script_text = " ".join(str(s) for s in scripts).lower()

        duration = 1.0  # base
        if any(kw in script_text for kw in ["apt-get", "apk add", "yum install"]):
            duration += 3.0
        if any(kw in script_text for kw in ["npm install", "npm ci", "yarn install"]):
            duration += 2.5
        if any(kw in script_text for kw in ["pip install", "poetry install", "conda install"]):
            duration += 2.0
        if any(kw in script_text for kw in ["docker build", "buildah", "kaniko"]):
            duration += 5.0
        if any(kw in script_text for kw in ["make", "cmake", "cargo build", "go build", "mvn", "gradle"]):
            duration += 8.0
        if any(kw in script_text for kw in ["test", "pytest", "jest", "rspec", "phpunit"]):
            duration += 4.0
        if any(kw in script_text for kw in ["deploy", "kubectl", "helm", "terraform"]):
            duration += 3.0
        if "echo" in script_text and duration == 1.0:
            duration = 0.5
        return min(duration, 20.0)  # cap at 20 min

    jobs = []
    total_minutes = 0
    for key in data:
        if key not in reserved and not key.startswith("."):
            if isinstance(data[key], dict):
                minutes = estimate_job_minutes(key, data[key])
                jobs.append({"name": key, "minutes": minutes})
                total_minutes += minutes

    if not jobs:
        return None

    total_hours = total_minutes / 60
    energy_kwh = (TDP_W * PUE * total_hours) / 1000
    operational_carbon = energy_kwh * CARBON_INTENSITY * 1000  # gCO2e
    embodied_carbon = EMBODIED_RATE * total_hours
    sci_score = operational_carbon + embodied_carbon

    # Estimate "after" with basic optimizations
    has_cache = "cache:" in str(content)
    has_interruptible = "interruptible:" in str(content)
    has_git_depth = "GIT_DEPTH" in str(content)
    has_alpine = "alpine" in str(content).lower()

    reduction = 0
    if not has_cache:
        reduction += 0.25  # cache saves ~25%
    if not has_alpine:
        reduction += 0.10  # lighter images
    if not has_git_depth:
        reduction += 0.05
    if not has_interruptible:
        reduction += 0.05
    reduction = min(reduction, 0.50)  # cap at 50%

    sci_after = sci_score * (1 - reduction)

    return {
        "job_count": len(jobs),
        "total_minutes": round(total_minutes, 1),
        "energy_kwh": round(energy_kwh, 6),
        "operational_carbon_gco2e": round(operational_carbon, 2),
        "embodied_carbon_gco2e": round(embodied_carbon, 2),
        "sci_before_gco2e": round(sci_score, 2),
        "sci_after_gco2e": round(sci_after, 2),
        "reduction_percent": round(reduction * 100, 1),
        "jobs": jobs,
    }


def generate_all(dataset_dir, output_dir=None):
    if output_dir is None:
        output_dir = dataset_dir
    output = Path(output_dir)
    
    dataset = load_dataset(dataset_dir)
    print(f"Loaded {len(dataset)} projects from dataset")

    # --- Compute stats ---
    waste_scores = [d.get("waste_score", 0) for d in dataset]
    pattern_counter = Counter()
    for d in dataset:
        for p in d.get("estimated_waste_patterns", []):
            pattern_counter[p] += 1

    total = len(dataset)
    no_cache = sum(1 for d in dataset if not d.get("has_cache", True))
    no_interruptible = sum(1 for d in dataset if not d.get("has_interruptible", True))
    no_timeout = sum(1 for d in dataset if not d.get("has_timeout", True))
    no_retry = sum(1 for d in dataset if not d.get("has_retry", True))
    no_shallow = sum(1 for d in dataset if not d.get("has_shallow_clone", True))
    no_needs = sum(1 for d in dataset if not d.get("has_needs", True))
    has_dind = sum(1 for d in dataset if d.get("has_docker_in_docker", False))
    job_counts = [d.get("job_count", 0) for d in dataset]

    # --- SCI calculations for all pipelines ---
    sci_results = []
    yaml_dir = Path(dataset_dir) / "yaml_files"
    for d in dataset:
        yaml_path = None
        # Try to find the yaml file
        if d.get("yaml_file"):
            yaml_path = Path(d["yaml_file"])
        if yaml_path is None or not yaml_path.exists():
            # Try by project path
            safe_name = d.get("project_path", "").replace("/", "_")
            yaml_path = yaml_dir / f"{safe_name}.gitlab-ci.yml"
        if not yaml_path or not yaml_path.exists():
            continue
            
        try:
            content = yaml_path.read_text()
        except:
            continue
            
        sci = calculate_sci_for_yaml(content)
        if sci:
            sci_results.append({
                "project_path": d.get("project_path", ""),
                "stars": d.get("stars", 0),
                "language": d.get("language", ""),
                "waste_score": d.get("waste_score", 0),
                **sci
            })

    # --- Compute SCI distribution ---
    sci_scores = [r["sci_before_gco2e"] for r in sci_results if r["sci_before_gco2e"] > 0]
    sci_after_scores = [r["sci_after_gco2e"] for r in sci_results if r["sci_after_gco2e"] > 0]

    # --- Percentile function ---
    def percentile(data, p):
        if not data:
            return 0
        sorted_d = sorted(data)
        k = (len(sorted_d) - 1) * p / 100
        f = int(k)
        c = f + 1 if f + 1 < len(sorted_d) else f
        return sorted_d[f] + (k - f) * (sorted_d[c] - sorted_d[f])

    # =========================================
    # OUTPUT 1: dataset_stats.yml (for prompt)
    # =========================================
    stats = {
        "dataset_info": {
            "total_projects": total,
            "collection_method": "GitLab API + public projects",
            "analysis_date": "2026-03-01",
        },
        "waste_patterns": {
            "average_waste_score": round(sum(waste_scores) / total, 1) if total else 0,
            "median_waste_score": round(percentile(waste_scores, 50), 1),
            "pattern_frequency": {
                p: {"count": c, "percent": round(c / total * 100, 1)}
                for p, c in pattern_counter.most_common()
            },
            "no_cache_percent": round(no_cache / total * 100, 1),
            "no_interruptible_percent": round(no_interruptible / total * 100, 1),
            "no_timeout_percent": round(no_timeout / total * 100, 1),
            "no_retry_percent": round(no_retry / total * 100, 1),
            "no_shallow_clone_percent": round(no_shallow / total * 100, 1),
            "docker_in_docker_percent": round(has_dind / total * 100, 1),
        },
        "pipeline_complexity": {
            "avg_jobs": round(sum(job_counts) / total, 1) if total else 0,
            "median_jobs": round(percentile(job_counts, 50), 1),
            "max_jobs": max(job_counts) if job_counts else 0,
        },
        "sci_distribution": {
            "projects_analyzed": len(sci_results),
            "avg_sci_before_gco2e": round(sum(sci_scores) / len(sci_scores), 2) if sci_scores else 0,
            "median_sci_before_gco2e": round(percentile(sci_scores, 50), 2) if sci_scores else 0,
            "p25_sci_gco2e": round(percentile(sci_scores, 25), 2) if sci_scores else 0,
            "p75_sci_gco2e": round(percentile(sci_scores, 75), 2) if sci_scores else 0,
            "p90_sci_gco2e": round(percentile(sci_scores, 90), 2) if sci_scores else 0,
            "avg_sci_after_gco2e": round(sum(sci_after_scores) / len(sci_after_scores), 2) if sci_after_scores else 0,
            "avg_reduction_percent": round(
                sum(r["reduction_percent"] for r in sci_results) / len(sci_results), 1
            ) if sci_results else 0,
            "total_monthly_savings_gco2e": round(
                sum((r["sci_before_gco2e"] - r["sci_after_gco2e"]) * 50 for r in sci_results), 0
            ) if sci_results else 0,
        },
        "benchmarks_for_agent": {
            "description": "Use these to compare a pipeline against the dataset",
            "excellent": "SCI < p25 — Better than 75% of pipelines",
            "good": "SCI between p25 and median — Better than average",
            "average": "SCI between median and p75 — Typical pipeline",
            "poor": "SCI between p75 and p90 — Worse than most",
            "critical": "SCI > p90 — Top 10% most wasteful pipelines",
        }
    }

    stats_path = output / "dataset_stats.yml"
    with open(stats_path, "w") as f:
        yaml.dump(stats, f, default_flow_style=False, sort_keys=False)
    print(f"✓ Wrote {stats_path}")

    # =========================================
    # OUTPUT 2: dataset_benchmarks.json (agent reads at runtime)
    # =========================================
    benchmarks = {
        "percentiles": {
            "p25": round(percentile(sci_scores, 25), 2) if sci_scores else 0,
            "p50": round(percentile(sci_scores, 50), 2) if sci_scores else 0,
            "p75": round(percentile(sci_scores, 75), 2) if sci_scores else 0,
            "p90": round(percentile(sci_scores, 90), 2) if sci_scores else 0,
        },
        "pattern_frequency_percent": {
            p: round(c / total * 100, 1)
            for p, c in pattern_counter.most_common()
        },
        "total_projects": total,
        "avg_waste_score": round(sum(waste_scores) / total, 1) if total else 0,
    }
    
    bench_path = output / "dataset_benchmarks.json"
    with open(bench_path, "w") as f:
        json.dump(benchmarks, f, indent=2)
    print(f"✓ Wrote {bench_path}")

    # =========================================
    # OUTPUT 3: batch_analysis_results.csv (research output)
    # =========================================
    csv_path = output / "batch_analysis_results.csv"
    with open(csv_path, "w") as f:
        headers = [
            "project_path", "stars", "language", "waste_score",
            "job_count", "total_minutes",
            "energy_kwh", "operational_carbon_gco2e", "embodied_carbon_gco2e",
            "sci_before_gco2e", "sci_after_gco2e", "reduction_percent"
        ]
        f.write(",".join(headers) + "\n")
        for r in sci_results:
            row = [
                r.get("project_path", ""),
                str(r.get("stars", 0)),
                str(r.get("language", "")),
                str(r.get("waste_score", 0)),
                str(r.get("job_count", 0)),
                str(r.get("total_minutes", 0)),
                str(r.get("energy_kwh", 0)),
                str(r.get("operational_carbon_gco2e", 0)),
                str(r.get("embodied_carbon_gco2e", 0)),
                str(r.get("sci_before_gco2e", 0)),
                str(r.get("sci_after_gco2e", 0)),
                str(r.get("reduction_percent", 0)),
            ]
            f.write(",".join(row) + "\n")
    print(f"✓ Wrote {csv_path}")

    # --- Print summary ---
    print(f"\n{'='*60}")
    print(f"DATASET ANALYSIS SUMMARY")
    print(f"{'='*60}")
    print(f"Projects analyzed: {len(sci_results)}/{total}")
    print(f"Avg waste score: {stats['waste_patterns']['average_waste_score']}/9")
    print(f"Top patterns:")
    for p, c in pattern_counter.most_common(5):
        print(f"  {p}: {c}/{total} ({c/total*100:.0f}%)")
    if sci_scores:
        print(f"\nSCI Distribution (gCO2e/pipeline run):")
        print(f"  P25:    {percentile(sci_scores, 25):.2f}")
        print(f"  Median: {percentile(sci_scores, 50):.2f}")
        print(f"  P75:    {percentile(sci_scores, 75):.2f}")
        print(f"  P90:    {percentile(sci_scores, 90):.2f}")
        print(f"  Avg before: {sum(sci_scores)/len(sci_scores):.2f}")
        print(f"  Avg after:  {sum(sci_after_scores)/len(sci_after_scores):.2f}")
        print(f"  Avg reduction: {stats['sci_distribution']['avg_reduction_percent']}%")
        print(f"  Est. total monthly savings (all 200 × 50 runs): "
              f"{stats['sci_distribution']['total_monthly_savings_gco2e']:.0f} gCO2e")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate dataset stats for GreenPipe")
    parser.add_argument("--dataset", default="dataset", help="Dataset directory")
    parser.add_argument("--output", default=None, help="Output directory (default: same as dataset)")
    args = parser.parse_args()
    generate_all(args.dataset, args.output)
