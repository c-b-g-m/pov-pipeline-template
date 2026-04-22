"""
Tests for main.py orchestration — specifically URL state management:
URLs must be marked processed only after successful PR creation, not after drafting.
"""

import sys
import pytest


# ─── Fixtures ────────────────────────────────────────────────────────────────

FAKE_CONFIG = {
    "author": {"name": "Test Author", "specialization": "Testing"},
    "pipeline": {"log_file": "pipeline.log", "rate_limit_sleep": 0},
    "discovery": {"max_candidates": 5},
    "drafting": {"output_format": "mdx"},
    "site": {},
}

FAKE_CANDIDATES = [
    {"url": "https://example.com/article-1", "title": "Article One", "theme": "theme-one", "summary": ""},
    {"url": "https://example.com/article-2", "title": "Article Two", "theme": "theme-two", "summary": ""},
]

FAKE_DRAFTS = [
    {"slug": "article-one", "content": "...", "metadata": {"theme": "theme-one", "description": "Desc one"}},
    {"slug": "article-two", "content": "...", "metadata": {"theme": "theme-two", "description": "Desc two"}},
]


def _patch_main(monkeypatch, tmp_path, *, candidates, drafts, pr_results):
    """
    Patch pipeline.main internals.

    pr_results: list of return values for successive create_pr calls.
                None = failure, a URL string = success.
    """
    import pipeline.main as main_module

    monkeypatch.setattr(main_module, "load_config", lambda path=None: FAKE_CONFIG)
    monkeypatch.setattr(main_module, "_setup_logging", lambda config: None)
    monkeypatch.setattr(main_module, "discover", lambda config, brave_api_key="": candidates)

    draft_iter = iter(drafts)
    monkeypatch.setattr(main_module, "draft_take",
                        lambda candidate, config, anthropic_key, firecrawl_key: next(draft_iter, None))

    pr_iter = iter(pr_results)
    monkeypatch.setattr(main_module, "create_pr",
                        lambda draft, config, site_repo_path: next(pr_iter, None))

    marked = []
    monkeypatch.setattr(main_module, "mark_processed", lambda urls: marked.extend(urls))

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("SITE_REPO_PATH", str(tmp_path))

    return marked


# ─── Tests ───────────────────────────────────────────────────────────────────

def test_all_prs_succeed_marks_all_urls(monkeypatch, tmp_path):
    marked = _patch_main(
        monkeypatch, tmp_path,
        candidates=FAKE_CANDIDATES,
        drafts=FAKE_DRAFTS,
        pr_results=["https://github.com/pr/1", "https://github.com/pr/2"],
    )
    sys.argv = ["pipeline.main"]
    import pipeline.main as main_module
    main_module.main()

    assert set(marked) == {"https://example.com/article-1", "https://example.com/article-2"}


def test_partial_pr_failure_marks_only_successful_urls(monkeypatch, tmp_path):
    marked = _patch_main(
        monkeypatch, tmp_path,
        candidates=FAKE_CANDIDATES,
        drafts=FAKE_DRAFTS,
        pr_results=["https://github.com/pr/1", None],  # second PR fails
    )
    sys.argv = ["pipeline.main"]
    import pipeline.main as main_module
    main_module.main()

    assert marked == ["https://example.com/article-1"]
    assert "https://example.com/article-2" not in marked


def test_all_prs_fail_marks_nothing(monkeypatch, tmp_path):
    marked = _patch_main(
        monkeypatch, tmp_path,
        candidates=FAKE_CANDIDATES,
        drafts=FAKE_DRAFTS,
        pr_results=[None, None],
    )
    sys.argv = ["pipeline.main"]
    import pipeline.main as main_module
    main_module.main()

    assert marked == []


def test_dry_run_marks_drafted_urls_without_creating_prs(monkeypatch, tmp_path):
    import pipeline.main as main_module

    monkeypatch.setattr(main_module, "load_config", lambda path=None: FAKE_CONFIG)
    monkeypatch.setattr(main_module, "_setup_logging", lambda config: None)
    monkeypatch.setattr(main_module, "discover", lambda config, brave_api_key="": FAKE_CANDIDATES)

    draft_iter = iter(FAKE_DRAFTS)
    monkeypatch.setattr(main_module, "draft_take",
                        lambda candidate, config, anthropic_key, firecrawl_key: next(draft_iter, None))

    pr_called = []
    monkeypatch.setattr(main_module, "create_pr", lambda *a, **kw: pr_called.append(True) or "url")

    marked = []
    monkeypatch.setattr(main_module, "mark_processed", lambda urls: marked.extend(urls))

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("SITE_REPO_PATH", str(tmp_path))

    sys.argv = ["pipeline.main", "--dry-run"]
    main_module.main()

    assert pr_called == [], "create_pr must not be called in dry-run mode"
    assert set(marked) == {"https://example.com/article-1", "https://example.com/article-2"}


def test_no_drafts_produced_marks_nothing(monkeypatch, tmp_path):
    marked = _patch_main(
        monkeypatch, tmp_path,
        candidates=FAKE_CANDIDATES,
        drafts=[None, None],  # both drafts fail
        pr_results=[],
    )
    sys.argv = ["pipeline.main"]
    import pipeline.main as main_module
    main_module.main()

    assert marked == []
