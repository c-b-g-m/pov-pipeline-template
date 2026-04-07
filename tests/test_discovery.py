"""Tests for discovery module."""

import os
import pytest
import yaml

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def _load_config():
    with open(os.path.join(FIXTURES, "sample_config.yaml"), "r") as f:
        return yaml.safe_load(f)


def test_matches_keywords():
    from pipeline.discovery import _matches_keywords
    assert _matches_keywords("This has alpha in it", ["alpha", "beta"])
    assert _matches_keywords("ALPHA uppercase", ["alpha"])
    assert not _matches_keywords("No match here", ["alpha", "beta"])
    assert not _matches_keywords("", ["alpha"])


def test_detect_theme():
    from pipeline.discovery import _detect_theme
    config = _load_config()
    theme_keywords = {t["slug"]: t["keywords"] for t in config["themes"]}

    assert _detect_theme("This article mentions alpha and beta trends", theme_keywords) == "theme-one"
    assert _detect_theme("Gamma and delta are discussed here", theme_keywords) == "theme-two"
    assert _detect_theme("Nothing relevant here at all", theme_keywords) is None


def test_is_blocked():
    from pipeline.discovery import _is_blocked
    blocked = frozenset(["linkedin.com", "facebook.com"])
    assert _is_blocked("https://linkedin.com/posts/123", blocked)
    assert _is_blocked("https://www.facebook.com/page", blocked)
    assert not _is_blocked("https://example.com/article", blocked)


def test_normalize_url():
    from pipeline.discovery import _normalize_url
    assert _normalize_url("https://www.example.com/path/") == "https://example.com/path"
    assert _normalize_url("https://example.com") == "https://example.com/"
    assert _normalize_url("https://example.com/path") == "https://example.com/path"


def test_is_index_url():
    from pipeline.discovery import _is_index_url
    assert _is_index_url("https://example.com/")
    assert _is_index_url("https://example.com/2026/04/")
    assert not _is_index_url("https://example.com/article-slug")
