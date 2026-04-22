"""Tests for pipeline/publisher.py."""

import subprocess
import pytest

import pipeline.publisher as publisher


SAMPLE_DRAFT = {
    "slug": "test-slug",
    "filename": "test-slug/index.html",
    "content": "<html>content</html>",
    "site_draft": "## Body\n\nSome text.",
    "linkedin_draft": "LinkedIn post text.",
    "metadata": {
        "title": "Test Article Title",
        "description": "Test description.",
        "theme": "strategy",
        "tags": ["tag1"],
        "source_url": "https://example.com/article",
        "publish_date": "2026-04-22",
    },
}

SAMPLE_CONFIG = {
    "site": {"domain": "example.com", "content_path": "content/pov"},
    "publishing": {"base_branch": "main", "branch_prefix": "pov"},
    "pipeline": {"timezone": "UTC"},
    "drafting": {"output_format": "html"},
}


class _RunQueue:
    """Mock for publisher._run; pops responses in order, returns success for extras."""

    def __init__(self, responses=None):
        self._responses = list(responses or [])
        self.calls = []

    def __call__(self, cmd, cwd=None):
        self.calls.append(list(cmd))
        if self._responses:
            rc, out, err = self._responses.pop(0)
        else:
            rc, out, err = 0, "", ""
        return subprocess.CompletedProcess(cmd, rc, stdout=out, stderr=err)


def _site_repo(tmp_path):
    content_dir = tmp_path / "content" / "pov"
    content_dir.mkdir(parents=True)
    return str(tmp_path)


# ─── create_pr ───────────────────────────────────────────────────────────────

def test_create_pr_missing_content_dir(monkeypatch, tmp_path):
    run = _RunQueue()
    monkeypatch.setattr(publisher, "_run", run)
    result = publisher.create_pr(SAMPLE_DRAFT, SAMPLE_CONFIG, str(tmp_path))
    assert result is None
    assert run.calls == []


def test_create_pr_checkout_failure(monkeypatch, tmp_path):
    repo_path = _site_repo(tmp_path)
    run = _RunQueue([(1, "", "error: pathspec 'main' did not match")])
    monkeypatch.setattr(publisher, "_run", run)
    result = publisher.create_pr(SAMPLE_DRAFT, SAMPLE_CONFIG, repo_path)
    assert result is None


def test_create_pr_dry_run_returns_sentinel(monkeypatch, tmp_path):
    repo_path = _site_repo(tmp_path)
    monkeypatch.setattr(publisher, "_run", _RunQueue())
    result = publisher.create_pr(SAMPLE_DRAFT, SAMPLE_CONFIG, repo_path, dry_run=True)
    assert result == "DRY_RUN"


def test_create_pr_dry_run_cleans_up_file(monkeypatch, tmp_path):
    repo_path = _site_repo(tmp_path)
    monkeypatch.setattr(publisher, "_run", _RunQueue())
    publisher.create_pr(SAMPLE_DRAFT, SAMPLE_CONFIG, repo_path, dry_run=True)
    file_path = tmp_path / "content" / "pov" / "test-slug" / "index.html"
    assert not file_path.exists()


def test_create_pr_social_draft_heading(monkeypatch, tmp_path):
    """PR body must use '### Social Draft' — Buffer workflow regex depends on this."""
    repo_path = _site_repo(tmp_path)
    pr_bodies = []

    def capture(cmd, cwd=None):
        if cmd[0] == "gh":
            pr_bodies.append(cmd[cmd.index("--body") + 1])
        stdout = "https://github.com/owner/repo/pull/1" if cmd[0] == "gh" else ""
        # git branch --list must return empty to skip collision branch
        if cmd[:2] == ["git", "branch"]:
            stdout = ""
        return subprocess.CompletedProcess(cmd, 0, stdout=stdout, stderr="")

    monkeypatch.setattr(publisher, "_run", capture)
    publisher.create_pr(SAMPLE_DRAFT, SAMPLE_CONFIG, repo_path)

    assert pr_bodies, "gh pr create was never called"
    assert "### Social Draft" in pr_bodies[0]
    assert "### LinkedIn Draft" not in pr_bodies[0]


def test_create_pr_title_truncated(monkeypatch, tmp_path):
    """PR title must not exceed len('POV: ') + 65 = 70 chars."""
    repo_path = _site_repo(tmp_path)
    draft = {**SAMPLE_DRAFT, "metadata": {**SAMPLE_DRAFT["metadata"], "title": "X" * 100}}
    pr_titles = []

    def capture(cmd, cwd=None):
        if cmd[0] == "gh":
            pr_titles.append(cmd[cmd.index("--title") + 1])
        stdout = "https://github.com/owner/repo/pull/1" if cmd[0] == "gh" else ""
        if cmd[:2] == ["git", "branch"]:
            stdout = ""
        return subprocess.CompletedProcess(cmd, 0, stdout=stdout, stderr="")

    monkeypatch.setattr(publisher, "_run", capture)
    publisher.create_pr(draft, SAMPLE_CONFIG, repo_path)

    assert pr_titles
    assert len(pr_titles[0]) <= 70


def test_create_pr_success_returns_url(monkeypatch, tmp_path):
    repo_path = _site_repo(tmp_path)
    pr_url = "https://github.com/owner/repo/pull/42"

    def succeed(cmd, cwd=None):
        stdout = pr_url if cmd[0] == "gh" else ""
        if cmd[:2] == ["git", "branch"]:
            stdout = ""
        return subprocess.CompletedProcess(cmd, 0, stdout=stdout, stderr="")

    monkeypatch.setattr(publisher, "_run", succeed)
    result = publisher.create_pr(SAMPLE_DRAFT, SAMPLE_CONFIG, repo_path)
    assert result == pr_url


def test_create_pr_push_failure_returns_none(monkeypatch, tmp_path):
    repo_path = _site_repo(tmp_path)
    # Responses: checkout, pull, branch --list, checkout -b, add, commit, push (fail)
    responses = [
        (0, "", ""),  # git checkout main
        (0, "", ""),  # git pull
        (0, "", ""),  # git branch --list (no collision)
        (0, "", ""),  # git checkout -b
        (0, "", ""),  # git add
        (0, "", ""),  # git commit
        (1, "", "error: failed to push"),  # git push — FAIL
    ]
    monkeypatch.setattr(publisher, "_run", _RunQueue(responses))
    result = publisher.create_pr(SAMPLE_DRAFT, SAMPLE_CONFIG, repo_path)
    assert result is None


# ─── create_manifest_pr ──────────────────────────────────────────────────────

def test_create_manifest_pr_skips_non_html(monkeypatch):
    config = {**SAMPLE_CONFIG, "drafting": {"output_format": "mdx"}}
    run = _RunQueue()
    monkeypatch.setattr(publisher, "_run", run)
    result = publisher.create_manifest_pr([SAMPLE_DRAFT], config, "/any/path")
    assert result is None
    assert run.calls == []


def test_create_manifest_pr_skips_duplicate_slugs(monkeypatch, tmp_path):
    import json
    repo_path = _site_repo(tmp_path)

    # Write a posts.json that already contains test-slug
    posts_json = tmp_path / "content" / "pov" / "posts.json"
    posts_json.write_text(json.dumps([{"slug": "test-slug", "title": "Old"}]))

    run = _RunQueue()
    monkeypatch.setattr(publisher, "_run", run)
    result = publisher.create_manifest_pr([SAMPLE_DRAFT], SAMPLE_CONFIG, repo_path)
    assert result is None
