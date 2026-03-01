#!/usr/bin/env python3
"""
GreenPipe Dataset Collector
Collects .gitlab-ci.yml files from public GitLab projects via the GitLab API.
Builds a dataset for carbon footprint analysis research.

Usage:
    python3 collect_gitlab_ci_dataset.py --token YOUR_GITLAB_TOKEN --output dataset/
    
No token needed for public projects (but rate-limited to 60 req/hr without token).
With token: 2000 req/hr.
"""

import requests
import json
import os
import time
import argparse
import yaml
import hashlib
from datetime import datetime
from pathlib import Path

GITLAB_API = "https://gitlab.com/api/v4"

# Categories of projects to collect (diverse pipeline types)
SEARCH_QUERIES = [
    # By language/framework
    "python django",
    "python flask", 
    "python fastapi",
    "node react",
    "node express",
    "java spring",
    "java maven",
    "go golang",
    "rust cargo",
    "ruby rails",
    "php laravel",
    "dotnet csharp",
    # By pipeline complexity
    "docker kubernetes deploy",
    "terraform infrastructure",
    "microservices",
    "monorepo",
    "machine learning mlops",
    "data pipeline",
    "mobile android ios",
    "embedded firmware",
    # By org type
    "open source library",
    "api backend",
    "frontend webapp",
    "documentation docs",
    "security scanning",
]

# Well-known large GitLab projects with complex pipelines
KNOWN_PROJECTS = [
    "gitlab-org/gitlab",
    "gitlab-org/gitlab-runner", 
    "gitlab-org/gitlab-pages",
    "gitlab-org/cli",
    "gnome/glib",
    "gnome/gtk",
    "gnome/gnome-shell",
    "freedesktop/mesa/mesa",
    "inkscape/inkscape",
    "fdroid/fdroidclient",
    "fdroid/fdroidserver",
    "tortoisegit/tortoisegit",
    "wireshark/wireshark",
    "libreoffice/core",
    "postmarketOS/pmaports",
    "veloren/veloren",
    "baserow/baserow",
    "calckey/calckey",
    "gitlab-org/omnibus-gitlab",
    "gitlab-org/gitaly",
]


def get_headers(token=None):
    headers = {"Accept": "application/json"}
    if token:
        headers["PRIVATE-TOKEN"] = token
    return headers


def search_projects(query, token=None, per_page=20):
    """Search GitLab for public projects matching query."""
    url = f"{GITLAB_API}/projects"
    params = {
        "search": query,
        "visibility": "public",
        "order_by": "star_count",
        "sort": "desc",
        "per_page": per_page,
        "with_issues_enabled": True,
    }
    try:
        resp = requests.get(url, headers=get_headers(token), params=params, timeout=30)
        if resp.status_code == 200:
            return resp.json()
        else:
            print(f"  [WARN] Search '{query}' returned {resp.status_code}")
            return []
    except Exception as e:
        print(f"  [ERROR] Search '{query}': {e}")
        return []


def get_file_content(project_id, file_path, ref="HEAD", token=None):
    """Get raw file content from a GitLab project."""
    import urllib.parse
    encoded_path = urllib.parse.quote(file_path, safe="")
    url = f"{GITLAB_API}/projects/{project_id}/repository/files/{encoded_path}/raw"
    params = {"ref": ref}
    try:
        resp = requests.get(url, headers=get_headers(token), params=params, timeout=30)
        if resp.status_code == 200:
            return resp.text
        return None
    except:
        return None


def get_project_by_path(path, token=None):
    """Get project info by its full path."""
    import urllib.parse
    encoded = urllib.parse.quote(path, safe="")
    url = f"{GITLAB_API}/projects/{encoded}"
    try:
        resp = requests.get(url, headers=get_headers(token), timeout=30)
        if resp.status_code == 200:
            return resp.json()
        return None
    except:
        return None


def get_pipeline_stats(project_id, token=None):
    """Get recent pipeline statistics for a project."""
    url = f"{GITLAB_API}/projects/{project_id}/pipelines"
    params = {"per_page": 20, "status": "success"}
    try:
        resp = requests.get(url, headers=get_headers(token), params=params, timeout=30)
        if resp.status_code == 200:
            pipelines = resp.json()
            durations = []
            for p in pipelines:
                if p.get("duration"):
                    durations.append(p["duration"])
            return {
                "total_pipelines_sampled": len(pipelines),
                "avg_duration_seconds": sum(durations) / len(durations) if durations else None,
                "min_duration_seconds": min(durations) if durations else None,
                "max_duration_seconds": max(durations) if durations else None,
                "durations": durations,
            }
        return None
    except:
        return None


def get_jobs_for_pipeline(project_id, pipeline_id, token=None):
    """Get job details for a specific pipeline."""
    url = f"{GITLAB_API}/projects/{project_id}/pipelines/{pipeline_id}/jobs"
    params = {"per_page": 100}
    try:
        resp = requests.get(url, headers=get_headers(token), params=params, timeout=30)
        if resp.status_code == 200:
            jobs = resp.json()
            return [
                {
                    "name": j.get("name"),
                    "stage": j.get("stage"),
                    "duration": j.get("duration"),
                    "status": j.get("status"),
                    "runner": j.get("runner", {}).get("description") if j.get("runner") else None,
                    "tag_list": j.get("tag_list", []),
                }
                for j in jobs
            ]
        return None
    except:
        return None


def analyze_ci_yaml(content):
    """Analyze a .gitlab-ci.yml file for carbon-relevant patterns."""
    patterns = {
        "has_cache": False,
        "has_artifacts": False,
        "has_rules": False,
        "has_only_except": False,
        "has_timeout": False,
        "has_interruptible": False,
        "has_retry": False,
        "has_resource_group": False,
        "has_parallel": False,
        "has_needs": False,
        "has_services": False,
        "has_docker_in_docker": False,
        "has_shallow_clone": False,
        "uses_pinned_images": False,
        "uses_alpine_images": False,
        "job_count": 0,
        "stage_count": 0,
        "estimated_waste_patterns": [],
        "waste_score": 0,
    }
    
    try:
        data = yaml.safe_load(content)
        if not isinstance(data, dict):
            return patterns
    except:
        return patterns
    
    # Count stages
    if "stages" in data:
        patterns["stage_count"] = len(data["stages"])
    
    content_lower = content.lower()
    
    # Check global patterns
    patterns["has_cache"] = "cache:" in content
    patterns["has_artifacts"] = "artifacts:" in content
    patterns["has_rules"] = "rules:" in content
    patterns["has_only_except"] = "only:" in content or "except:" in content
    patterns["has_timeout"] = "timeout:" in content
    patterns["has_interruptible"] = "interruptible:" in content
    patterns["has_retry"] = "retry:" in content
    patterns["has_resource_group"] = "resource_group:" in content
    patterns["has_parallel"] = "parallel:" in content
    patterns["has_needs"] = "needs:" in content
    patterns["has_services"] = "services:" in content
    patterns["has_docker_in_docker"] = "docker:dind" in content or "docker-in-docker" in content_lower
    patterns["has_shallow_clone"] = "GIT_DEPTH" in content
    
    # Check image patterns
    pinned = 0
    alpine = 0
    image_count = 0
    for line in content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("image:") or stripped.startswith("- name:"):
            image_count += 1
            if ":" in stripped and "@sha256:" in stripped:
                pinned += 1
            if "alpine" in stripped.lower():
                alpine += 1
    
    if image_count > 0:
        patterns["uses_pinned_images"] = pinned > 0
        patterns["uses_alpine_images"] = alpine > 0
    
    # Count jobs (keys that aren't reserved keywords)
    reserved = {
        "stages", "variables", "image", "services", "before_script",
        "after_script", "cache", "include", "default", "workflow",
        "pages", ".pre", ".post",
    }
    job_count = 0
    for key in data:
        if key not in reserved and not key.startswith("."):
            if isinstance(data[key], dict):
                job_count += 1
            elif isinstance(data[key], type(None)):
                pass  # skip null entries
    patterns["job_count"] = max(job_count, 0)
    
    # Identify waste patterns
    waste = []
    if not patterns["has_cache"]:
        waste.append("NO_CACHE")
    if not patterns["has_interruptible"]:
        waste.append("NO_INTERRUPTIBLE")
    if not patterns["has_timeout"]:
        waste.append("NO_TIMEOUT")
    if not patterns["has_retry"]:
        waste.append("NO_RETRY")
    if not patterns["has_shallow_clone"]:
        waste.append("NO_SHALLOW_CLONE")
    if not patterns["has_needs"] and patterns["job_count"] > 3:
        waste.append("NO_DAG_NEEDS")
    if patterns["has_docker_in_docker"]:
        waste.append("DOCKER_IN_DOCKER")
    if patterns["has_only_except"] and not patterns["has_rules"]:
        waste.append("LEGACY_ONLY_EXCEPT")
    if not patterns["uses_alpine_images"] and image_count > 0:
        waste.append("NO_ALPINE_IMAGES")
    
    patterns["estimated_waste_patterns"] = waste
    patterns["waste_score"] = len(waste)  # Higher = more waste
    
    return patterns


def collect_dataset(token=None, output_dir="dataset", max_projects=200):
    """Main collection function."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    (output / "yaml_files").mkdir(exist_ok=True)
    
    dataset = []
    seen_ids = set()
    
    print("=" * 60)
    print("GreenPipe Dataset Collector")
    print(f"Target: {max_projects} projects")
    print("=" * 60)
    
    # Phase 1: Collect from known projects
    print("\n[Phase 1] Collecting from known large projects...")
    for path in KNOWN_PROJECTS:
        if len(seen_ids) >= max_projects:
            break
        print(f"  Fetching: {path}")
        project = get_project_by_path(path, token)
        if project and project["id"] not in seen_ids:
            ci_content = get_file_content(project["id"], ".gitlab-ci.yml", token=token)
            if ci_content:
                seen_ids.add(project["id"])
                analysis = analyze_ci_yaml(ci_content)
                
                # Save YAML file
                safe_name = path.replace("/", "_")
                yaml_path = output / "yaml_files" / f"{safe_name}.gitlab-ci.yml"
                with open(yaml_path, "w") as f:
                    f.write(ci_content)
                
                # Get pipeline stats
                stats = get_pipeline_stats(project["id"], token)
                
                entry = {
                    "project_id": project["id"],
                    "project_path": project["path_with_namespace"],
                    "project_name": project["name"],
                    "stars": project.get("star_count", 0),
                    "forks": project.get("forks_count", 0),
                    "language": project.get("language"),
                    "created_at": project.get("created_at"),
                    "last_activity_at": project.get("last_activity_at"),
                    "ci_yaml_size_bytes": len(ci_content),
                    "ci_yaml_lines": ci_content.count("\n") + 1,
                    "ci_yaml_hash": hashlib.md5(ci_content.encode()).hexdigest(),
                    "yaml_file": str(yaml_path),
                    "pipeline_stats": stats,
                    **analysis,
                }
                dataset.append(entry)
                print(f"    ✓ {analysis['job_count']} jobs, {analysis['waste_score']} waste patterns")
            time.sleep(0.5)  # Rate limit
    
    # Phase 2: Search-based collection
    print(f"\n[Phase 2] Searching for projects by category...")
    for query in SEARCH_QUERIES:
        if len(seen_ids) >= max_projects:
            break
        print(f"\n  Searching: '{query}'")
        projects = search_projects(query, token, per_page=20)
        
        for project in projects:
            if len(seen_ids) >= max_projects:
                break
            if project["id"] in seen_ids:
                continue
            
            ci_content = get_file_content(project["id"], ".gitlab-ci.yml", token=token)
            if ci_content:
                seen_ids.add(project["id"])
                analysis = analyze_ci_yaml(ci_content)
                
                safe_name = f"{project['id']}_{project['path']}"
                yaml_path = output / "yaml_files" / f"{safe_name}.gitlab-ci.yml"
                with open(yaml_path, "w") as f:
                    f.write(ci_content)
                
                stats = get_pipeline_stats(project["id"], token)
                
                entry = {
                    "project_id": project["id"],
                    "project_path": project["path_with_namespace"],
                    "project_name": project["name"],
                    "stars": project.get("star_count", 0),
                    "forks": project.get("forks_count", 0),
                    "language": project.get("language"),
                    "search_category": query,
                    "created_at": project.get("created_at"),
                    "last_activity_at": project.get("last_activity_at"),
                    "ci_yaml_size_bytes": len(ci_content),
                    "ci_yaml_lines": ci_content.count("\n") + 1,
                    "ci_yaml_hash": hashlib.md5(ci_content.encode()).hexdigest(),
                    "yaml_file": str(yaml_path),
                    "pipeline_stats": stats,
                    **analysis,
                }
                dataset.append(entry)
                print(f"    ✓ {project['path_with_namespace']} ({analysis['job_count']} jobs, waste={analysis['waste_score']})")
            time.sleep(0.3)
    
    # Save dataset
    dataset_file = output / "greenpipe_dataset.json"
    with open(dataset_file, "w") as f:
        json.dump(dataset, f, indent=2, default=str)
    
    # Save summary CSV
    csv_file = output / "greenpipe_dataset_summary.csv"
    with open(csv_file, "w") as f:
        headers = [
            "project_id", "project_path", "stars", "language",
            "ci_yaml_lines", "job_count", "stage_count",
            "has_cache", "has_interruptible", "has_timeout",
            "has_retry", "has_shallow_clone", "has_needs",
            "has_docker_in_docker", "uses_alpine_images",
            "waste_score", "waste_patterns",
            "avg_pipeline_duration_s"
        ]
        f.write(",".join(headers) + "\n")
        for entry in dataset:
            avg_dur = ""
            if entry.get("pipeline_stats") and entry["pipeline_stats"].get("avg_duration_seconds"):
                avg_dur = str(round(entry["pipeline_stats"]["avg_duration_seconds"], 1))
            row = [
                str(entry["project_id"]),
                entry["project_path"],
                str(entry.get("stars", 0)),
                str(entry.get("language", "")),
                str(entry["ci_yaml_lines"]),
                str(entry["job_count"]),
                str(entry["stage_count"]),
                str(entry["has_cache"]),
                str(entry["has_interruptible"]),
                str(entry["has_timeout"]),
                str(entry["has_retry"]),
                str(entry["has_shallow_clone"]),
                str(entry["has_needs"]),
                str(entry["has_docker_in_docker"]),
                str(entry["uses_alpine_images"]),
                str(entry["waste_score"]),
                "|".join(entry["estimated_waste_patterns"]),
                avg_dur,
            ]
            f.write(",".join(row) + "\n")
    
    print("\n" + "=" * 60)
    print(f"Dataset collected: {len(dataset)} projects")
    print(f"JSON: {dataset_file}")
    print(f"CSV:  {csv_file}")
    print(f"YAML files: {output / 'yaml_files'}/")
    print("=" * 60)
    
    # Print quick stats
    if dataset:
        avg_waste = sum(d["waste_score"] for d in dataset) / len(dataset)
        avg_jobs = sum(d["job_count"] for d in dataset) / len(dataset)
        print(f"\nQuick Stats:")
        print(f"  Avg waste score: {avg_waste:.1f}")
        print(f"  Avg jobs per pipeline: {avg_jobs:.1f}")
        print(f"  Projects with no cache: {sum(1 for d in dataset if not d['has_cache'])}")
        print(f"  Projects with no interruptible: {sum(1 for d in dataset if not d['has_interruptible'])}")
        print(f"  Projects with DinD: {sum(1 for d in dataset if d['has_docker_in_docker'])}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GreenPipe Dataset Collector")
    parser.add_argument("--token", help="GitLab personal access token (optional, increases rate limit)")
    parser.add_argument("--output", default="dataset", help="Output directory")
    parser.add_argument("--max", type=int, default=200, help="Max projects to collect")
    args = parser.parse_args()
    
    collect_dataset(token=args.token, output_dir=args.output, max_projects=args.max)
