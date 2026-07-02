import re
import shutil
import stat
import subprocess
import os
import requests

from . import config


def parse_github_url(url: str):
    """Extract (owner, repo) from any common GitHub URL format."""
    url = url.strip().rstrip("/")
    match = re.search(r"github\.com[/:]([^/]+)/([^/]+?)(\.git)?$", url)
    if not match:
        raise ValueError(f"Not a valid GitHub URL: {url}")
    return match.group(1), match.group(2)


def _force_remove_readonly(func, path, exc_info):
    """
    shutil.rmtree error handler for Windows: git marks files inside .git/objects
    (pack files, etc.) read-only, which makes plain rmtree fail with
    'WinError 5: Access is denied'. This clears the read-only bit and retries.
    """
    os.chmod(path, stat.S_IWRITE)
    func(path)


def _safe_rmtree(path: str):
    shutil.rmtree(path, onerror=_force_remove_readonly)


def clone_repository(github_url: str):
    """Shallow-clone a public repo. Returns (repo_id, local_path)."""
    owner, repo = parse_github_url(github_url)
    repo_id = f"{owner}__{repo}"
    dest = os.path.join(config.REPO_CLONE_DIR, repo_id)

    if os.path.exists(dest):
        try:
            _safe_rmtree(dest)
        except OSError as e:
            raise RuntimeError(
                f"Could not remove the previous clone at '{dest}' before re-cloning. "
                f"Close any programs (editors, terminals, antivirus scans) that might have "
                f"a file open inside that folder, then try again. Details: {e}"
            )

    clone_url = f"https://github.com/{owner}/{repo}.git"
    result = subprocess.run(
        ["git", "clone", "--depth", "1", clone_url, dest],
        capture_output=True, text=True, timeout=300,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git clone failed for {github_url}. Is it a public repo? "
            f"Details: {result.stderr.strip()[:300]}"
        )

    return repo_id, dest


def fetch_issues(owner: str, repo: str, max_issues: int = 30):
    """Fetch issues (not pull requests) via the GitHub REST API."""
    headers = {"Accept": "application/vnd.github+json"}
    if config.GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {config.GITHUB_TOKEN}"

    issues = []
    url = f"https://api.github.com/repos/{owner}/{repo}/issues"
    params = {"state": "all", "per_page": max_issues, "sort": "updated"}
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=20)
        resp.raise_for_status()
        for item in resp.json():
            if "pull_request" in item:
                continue  # skip PRs, keep true issues only
            body = (item.get("body") or "").strip()
            issues.append({
                "number": item["number"],
                "title": item["title"],
                "body": body,
                "state": item["state"],
                "url": item["html_url"],
            })
    except requests.RequestException as e:
        print(f"[warn] could not fetch issues for {owner}/{repo}: {e}")

    return issues
