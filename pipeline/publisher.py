"""
Publisher module — creates GitHub PRs in the target site repo.

Flow per article:
  1. Create a new branch in the local site repo clone
  2. Write the article HTML file only — posts.json is NOT touched here
  3. Commit and push the branch
  4. Open a PR via `gh` CLI

Flow for the manifest PR (HTML output only):
  After all article PRs are created, create_manifest_pr() opens one additional
  PR that updates posts.json with all new entries. This keeps posts.json out of
  individual article PRs, preventing merge conflicts when multiple PRs land on
  the same base commit.
"""

import json
import logging
import os
import subprocess
from datetime import datetime
from typing import List, Optional

import pytz

log = logging.getLogger(__name__)


def _run(cmd: List[str], cwd: str = None) -> subprocess.CompletedProcess:
    log.debug("Running: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    if result.returncode != 0:
        log.error("Command failed: %s\nstderr: %s", " ".join(cmd), result.stderr)
    return result


def create_pr(draft: dict, config: dict, repo_path: str, dry_run: bool = False) -> Optional[str]:
    """
    Create a GitHub PR for a single article draft.

    Writes only the article HTML file — posts.json is handled separately by
    create_manifest_pr() after all article PRs are created.

    Args:
        draft: Output from drafter.draft_take()
        config: Pipeline config dict
        repo_path: Absolute path to the site repo
        dry_run: If True, write the file but don't push or create PR

    Returns:
        PR URL on success, None on failure
    """
    publishing = config.get("publishing", {})
    site = config.get("site", {})
    tz = pytz.timezone(config.get("pipeline", {}).get("timezone", "UTC"))

    content_path = site.get("content_path", "src/content/pov")
    base_branch = publishing.get("base_branch", "main")
    branch_prefix = publishing.get("branch_prefix", "pov")

    content_dir = os.path.join(repo_path, content_path)
    if not os.path.isdir(content_dir):
        log.error("Content directory does not exist: %s", content_dir)
        return None

    today = datetime.now(tz).strftime("%Y-%m-%d")
    base_branch_name = f"{branch_prefix}/{today}-{draft['slug']}"
    branch_name = base_branch_name
    file_path = os.path.join(content_dir, draft["filename"])
    relative_path = os.path.join(content_path, draft["filename"])

    # Ensure we're on base branch and up to date
    result = _run(["git", "checkout", base_branch], cwd=repo_path)
    if result.returncode != 0:
        log.error("Failed to checkout %s", base_branch)
        return None

    _run(["git", "pull", "origin", base_branch], cwd=repo_path)

    # Resolve branch name collision (same slug, same day)
    suffix = 2
    while _run(["git", "branch", "--list", branch_name], cwd=repo_path).stdout.strip():
        branch_name = f"{base_branch_name}-{suffix}"
        suffix += 1
    if branch_name != base_branch_name:
        log.warning("Branch %s already exists, using %s", base_branch_name, branch_name)

    # Create and checkout new branch
    result = _run(["git", "checkout", "-b", branch_name], cwd=repo_path)
    if result.returncode != 0:
        log.error("Failed to create branch %s", branch_name)
        return None

    # Write article file only (create parent dirs for slug/index.html structure)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w") as f:
        f.write(draft["content"])
    log.info("Wrote content file: %s", file_path)

    if dry_run:
        log.info("[DRY RUN] Would create PR for: %s", draft["metadata"]["title"])
        if os.path.exists(file_path):
            os.remove(file_path)
            parent = os.path.dirname(file_path)
            if os.path.isdir(parent) and not os.listdir(parent):
                os.rmdir(parent)
        _run(["git", "checkout", base_branch], cwd=repo_path)
        _run(["git", "branch", "-D", branch_name], cwd=repo_path)
        return "DRY_RUN"

    _run(["git", "add", relative_path], cwd=repo_path)

    commit_msg = f"Add POV take: {draft['metadata']['title']}"
    result = _run(["git", "commit", "-m", commit_msg], cwd=repo_path)
    if result.returncode != 0:
        log.error("Failed to commit")
        _run(["git", "restore", "--staged", relative_path], cwd=repo_path)
        _run(["git", "checkout", base_branch], cwd=repo_path)
        _run(["git", "branch", "-D", branch_name], cwd=repo_path)
        if os.path.exists(file_path):
            os.remove(file_path)
            parent = os.path.dirname(file_path)
            if os.path.isdir(parent) and not os.listdir(parent):
                os.rmdir(parent)
        return None

    result = _run(["git", "push", "-u", "origin", branch_name], cwd=repo_path)
    if result.returncode != 0:
        log.error("Failed to push branch %s", branch_name)
        _run(["git", "checkout", base_branch], cwd=repo_path)
        _run(["git", "branch", "-D", branch_name], cwd=repo_path)
        return None

    meta = draft["metadata"]
    pr_body = f"""## POV Take: {meta['title']}

**Theme:** {meta['theme']}
**Source:** [{meta['title']}]({meta['source_url']})
**Tags:** {', '.join(meta['tags'])}

---

{draft.get('site_draft', '')}

---

### Social Draft

```
{draft.get('linkedin_draft', 'No social draft generated.')}
```

---

*Auto-generated by pov-pipeline. Review, edit if needed, and merge to publish.*
*Merge the manifest PR (`pov/manifest-update-*`) after all article PRs are merged to update the post listing.*"""

    result = _run([
        "gh", "pr", "create",
        "--title", f"POV: {meta['title'][:65]}",
        "--body", pr_body,
        "--base", base_branch,
        "--head", branch_name,
    ], cwd=repo_path)

    _run(["git", "checkout", base_branch], cwd=repo_path)

    if result.returncode == 0:
        pr_url = result.stdout.strip()
        log.info("Created PR: %s", pr_url)
        return pr_url
    else:
        log.error("Failed to create PR: %s", result.stderr)
        return None


def create_manifest_pr(drafts: List[dict], config: dict, repo_path: str) -> Optional[str]:
    """
    Create a single PR that prepends all new entries to posts.json.

    Must be called after all article PRs are created (not necessarily merged).
    The user merges article PRs first, then merges this PR last to update the
    post listing. Because no article PR touches posts.json, this PR will never
    conflict with them.

    Args:
        drafts: List of draft dicts from drafter.draft_take()
        config: Pipeline config dict
        repo_path: Absolute path to the site repo

    Returns:
        PR URL on success, None on failure
    """
    from .formatters import build_posts_entry

    output_format = config.get("drafting", {}).get("output_format", "mdx")
    if output_format != "html":
        return None

    publishing = config.get("publishing", {})
    site = config.get("site", {})
    tz = pytz.timezone(config.get("pipeline", {}).get("timezone", "UTC"))

    content_path = site.get("content_path", "src/content/pov")
    base_branch = publishing.get("base_branch", "main")
    today = datetime.now(tz).strftime("%Y-%m-%d")
    branch_name = f"pov/manifest-update-{today}"

    posts_json_rel = os.path.join(content_path, "posts.json")
    posts_json_path = os.path.join(repo_path, posts_json_rel)

    result = _run(["git", "checkout", base_branch], cwd=repo_path)
    if result.returncode != 0:
        log.error("Failed to checkout %s for manifest PR", base_branch)
        return None

    _run(["git", "pull", "origin", base_branch], cwd=repo_path)

    result = _run(["git", "checkout", "-b", branch_name], cwd=repo_path)
    if result.returncode != 0:
        log.error("Failed to create manifest branch %s", branch_name)
        return None

    # Load existing posts.json
    try:
        if os.path.exists(posts_json_path):
            with open(posts_json_path) as f:
                posts = json.load(f)
        else:
            posts = []
    except (json.JSONDecodeError, OSError) as e:
        log.warning("Could not read posts.json (%s) — starting fresh", e)
        posts = []

    # Prepend new entries (newest first, deduplicated by slug)
    new_entries = [build_posts_entry(d) for d in drafts]
    existing_slugs = {p["slug"] for p in posts}
    added = []
    for entry in new_entries:
        if entry["slug"] not in existing_slugs:
            posts.insert(0, entry)
            existing_slugs.add(entry["slug"])
            added.append(entry["slug"])

    if not added:
        log.info("No new entries to add to posts.json — skipping manifest PR")
        _run(["git", "checkout", base_branch], cwd=repo_path)
        _run(["git", "branch", "-D", branch_name], cwd=repo_path)
        return None

    try:
        with open(posts_json_path, "w") as f:
            json.dump(posts, f, indent=2, ensure_ascii=False)
            f.write("\n")
    except OSError as e:
        log.error("Failed to write posts.json: %s", e)
        _run(["git", "checkout", base_branch], cwd=repo_path)
        return None

    _run(["git", "add", posts_json_rel], cwd=repo_path)

    result = _run(["git", "commit", "-m", f"Update posts.json: add {len(added)} new POV take(s)"], cwd=repo_path)
    if result.returncode != 0:
        log.error("Failed to commit manifest update")
        _run(["git", "checkout", base_branch], cwd=repo_path)
        return None

    result = _run(["git", "push", "-u", "origin", branch_name], cwd=repo_path)
    if result.returncode != 0:
        log.error("Failed to push manifest branch")
        _run(["git", "checkout", base_branch], cwd=repo_path)
        return None

    titles = "\n".join(f"- {d['metadata']['title']}" for d in drafts)
    pr_body = f"""## posts.json manifest update

Updates `{posts_json_rel}` to include {len(added)} new POV take(s).

**Merge this PR after all article PRs for this run are merged.**

### New entries
{titles}

---

*Auto-generated by pov-pipeline.*"""

    result = _run([
        "gh", "pr", "create",
        "--title", f"Update POV manifest — {today} ({len(added)} takes)",
        "--body", pr_body,
        "--base", base_branch,
        "--head", branch_name,
    ], cwd=repo_path)

    _run(["git", "checkout", base_branch], cwd=repo_path)

    if result.returncode == 0:
        pr_url = result.stdout.strip()
        log.info("Created manifest PR: %s", pr_url)
        return pr_url
    else:
        log.error("Failed to create manifest PR: %s", result.stderr)
        return None
