#!/usr/bin/env python3
"""
Alternative collector: Scrapes .gitlab-ci.yml files from GitHub mirrors.
Many GitLab projects are mirrored on GitHub. This uses GitHub's code search API.

Usage:
    python3 github_gitlab_ci_collector.py --token YOUR_GITHUB_TOKEN --output dataset/

GitHub token is required for code search API.
"""

import requests
import json
import time
import base64
import os
from pathlib import Path

GITHUB_API = "https://api.github.com"

# GitHub search queries to find .gitlab-ci.yml files
SEARCH_QUERIES = [
    # Find complex pipelines by content patterns
    'filename:.gitlab-ci.yml "stages:" "cache:" "artifacts:"',
    'filename:.gitlab-ci.yml "docker:dind" "services:"',
    'filename:.gitlab-ci.yml "deploy" "kubernetes" "helm"',
    'filename:.gitlab-ci.yml "terraform" "plan" "apply"',
    'filename:.gitlab-ci.yml "npm" "node" "test"',
    'filename:.gitlab-ci.yml "pip install" "python" "pytest"',
    'filename:.gitlab-ci.yml "maven" "java" "build"',
    'filename:.gitlab-ci.yml "go build" "golang"',
    'filename:.gitlab-ci.yml "cargo" "rust"',
    'filename:.gitlab-ci.yml "parallel:" "needs:"',
    'filename:.gitlab-ci.yml "include:" "template:"',
    'filename:.gitlab-ci.yml "machine learning" "train"',
    'filename:.gitlab-ci.yml "SAST" "security" "scanning"',
    'filename:.gitlab-ci.yml "pages" "hugo"',
    'filename:.gitlab-ci.yml "docker build" "registry"',
]


def search_github_code(query, token, per_page=30, page=1):
    """Search GitHub for .gitlab-ci.yml files."""
    url = f"{GITHUB_API}/search/code"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    params = {"q": query, "per_page": per_page, "page": page}
    
    resp = requests.get(url, headers=headers, params=params, timeout=30)
    if resp.status_code == 200:
        return resp.json()
    elif resp.status_code == 403:
        # Rate limited
        reset = resp.headers.get("X-RateLimit-Reset")
        print(f"  Rate limited. Reset at: {reset}")
        time.sleep(60)
        return None
    else:
        print(f"  Error: {resp.status_code}")
        return None


def get_file_content(repo_full_name, file_path, token):
    """Get file content from GitHub."""
    import urllib.parse
    encoded = urllib.parse.quote(file_path, safe="")
    url = f"{GITHUB_API}/repos/{repo_full_name}/contents/{encoded}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    
    resp = requests.get(url, headers=headers, timeout=30)
    if resp.status_code == 200:
        data = resp.json()
        if data.get("encoding") == "base64":
            return base64.b64decode(data["content"]).decode("utf-8", errors="replace")
    return None


def collect(token, output_dir="dataset", max_files=200):
    """Main collection."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    (output / "yaml_files").mkdir(exist_ok=True)
    
    collected = []
    seen = set()
    
    print(f"Collecting up to {max_files} .gitlab-ci.yml files from GitHub...")
    
    for query in SEARCH_QUERIES:
        if len(collected) >= max_files:
            break
        
        print(f"\nSearching: {query[:60]}...")
        result = search_github_code(query, token)
        if not result:
            continue
        
        for item in result.get("items", []):
            if len(collected) >= max_files:
                break
            
            repo = item["repository"]["full_name"]
            if repo in seen:
                continue
            seen.add(repo)
            
            content = get_file_content(repo, item["path"], token)
            if content and len(content) > 50:  # Skip trivial files
                safe_name = repo.replace("/", "_")
                filepath = output / "yaml_files" / f"{safe_name}.gitlab-ci.yml"
                with open(filepath, "w") as f:
                    f.write(content)
                
                collected.append({
                    "repo": repo,
                    "file_path": item["path"],
                    "source": "github_mirror",
                    "stars": item["repository"].get("stargazers_count", 0),
                    "size_bytes": len(content),
                    "lines": content.count("\n") + 1,
                    "local_path": str(filepath),
                })
                print(f"  ✓ {repo} ({content.count(chr(10))+1} lines)")
            
            time.sleep(2)  # GitHub code search rate limit: 10 req/min
    
    # Save index
    with open(output / "github_collection_index.json", "w") as f:
        json.dump(collected, f, indent=2)
    
    print(f"\nCollected {len(collected)} files")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--token", required=True, help="GitHub personal access token")
    parser.add_argument("--output", default="dataset")
    parser.add_argument("--max", type=int, default=200)
    args = parser.parse_args()
    collect(args.token, args.output, args.max)
