"""Tests for the pre-flight validate() helper in pipeline.main."""

import os
import subprocess

import pytest
import yaml

import pipeline.config_loader as config_loader
import pipeline.drafter as drafter
import pipeline.main as main_module
from pipeline.main import validate


def _write_valid_config(tmp_path):
    """Write a minimally valid config.yaml under tmp_path and return its path."""
    config = {
        "author": {"name": "A", "role": "r", "specialization": "s"},
        "site": {"domain": "example.com", "content_path": "content/posts"},
        "discovery": {"rss_feeds": [{"url": "https://example.com/feed"}]},
        "themes": [{"slug": "ai", "keywords": ["ai"]}],
    }
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config))
    return str(path)


@pytest.fixture
def clean_state(monkeypatch, tmp_path):
    """Reset config cache, set sane env, stub gh CLI to pass, stub voice-guidelines path."""
    config_loader._CONFIG_CACHE = None

    # Site repo with content_path present
    site_repo = tmp_path / "site"
    (site_repo / "content" / "posts").mkdir(parents=True)

    # Voice guidelines file present
    voice_path = tmp_path / "voice-guidelines.md"
    voice_path.write_text("# voice")
    monkeypatch.setattr(drafter, "VOICE_GUIDELINES_PATH", str(voice_path))

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("SITE_REPO_PATH", str(site_repo))

    # gh CLI present and authenticated
    monkeypatch.setattr(main_module.shutil, "which", lambda cmd: "/usr/bin/gh" if cmd == "gh" else None)

    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 0, stdout="Logged in", stderr="")
    monkeypatch.setattr(main_module.subprocess, "run", fake_run)

    return {
        "tmp_path": tmp_path,
        "site_repo": site_repo,
        "voice_path": voice_path,
    }


def test_validate_clean_pass(clean_state, tmp_path):
    config_path = _write_valid_config(tmp_path)
    errors = validate(config_path)
    assert errors == []


def test_validate_missing_anthropic_key(clean_state, monkeypatch, tmp_path):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    config_path = _write_valid_config(tmp_path)
    errors = validate(config_path)
    assert any("ANTHROPIC_API_KEY" in e for e in errors)


def test_validate_missing_voice_guidelines(clean_state, monkeypatch, tmp_path):
    monkeypatch.setattr(drafter, "VOICE_GUIDELINES_PATH", str(tmp_path / "does-not-exist.md"))
    config_path = _write_valid_config(tmp_path)
    errors = validate(config_path)
    assert any("voice-guidelines.md" in e for e in errors)


def test_validate_missing_site_repo_path(clean_state, monkeypatch, tmp_path):
    monkeypatch.delenv("SITE_REPO_PATH", raising=False)
    config_path = _write_valid_config(tmp_path)
    errors = validate(config_path)
    assert any("SITE_REPO_PATH is not set" in e for e in errors)


def test_validate_site_repo_path_missing_dir(clean_state, monkeypatch, tmp_path):
    monkeypatch.setenv("SITE_REPO_PATH", str(tmp_path / "nope"))
    config_path = _write_valid_config(tmp_path)
    errors = validate(config_path)
    assert any("SITE_REPO_PATH does not exist" in e for e in errors)


def test_validate_content_path_missing(clean_state, monkeypatch, tmp_path):
    bare_site = tmp_path / "bare_site"
    bare_site.mkdir()
    monkeypatch.setenv("SITE_REPO_PATH", str(bare_site))
    config_path = _write_valid_config(tmp_path)
    errors = validate(config_path)
    assert any("content_path" in e for e in errors)


def test_validate_gh_not_installed(clean_state, monkeypatch, tmp_path):
    monkeypatch.setattr(main_module.shutil, "which", lambda cmd: None)
    config_path = _write_valid_config(tmp_path)
    errors = validate(config_path)
    assert any("`gh` CLI not found" in e for e in errors)


def test_validate_gh_not_authenticated(clean_state, monkeypatch, tmp_path):
    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="not logged in")
    monkeypatch.setattr(main_module.subprocess, "run", fake_run)
    config_path = _write_valid_config(tmp_path)
    errors = validate(config_path)
    assert any("not authenticated" in e for e in errors)
