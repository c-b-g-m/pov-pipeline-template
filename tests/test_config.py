"""Tests for config_loader module."""

import os
import pytest
import yaml

from pipeline.config_loader import _validate

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def _base_config():
    """Minimum valid config dict — used as a base for validation tests."""
    return {
        "author": {"name": "A", "role": "r", "specialization": "s"},
        "site": {"domain": "d", "content_path": "c"},
        "discovery": {"rss_feeds": [{"url": "https://example.com/feed"}]},
        "themes": [{"slug": "t", "keywords": ["k"]}],
    }


def _load_yaml(path):
    with open(path, "r") as f:
        return yaml.safe_load(f)


def test_sample_config_loads():
    """Sample config should load without errors."""
    config = _load_yaml(os.path.join(FIXTURES, "sample_config.yaml"))
    assert config["author"]["name"] == "Test Author"
    assert config["site"]["domain"] == "testsite.dev"


def test_example_config_loads():
    """The shipped config.example.yaml should be valid."""
    example_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.example.yaml")
    config = _load_yaml(example_path)
    assert config["author"]["name"]
    assert config["site"]["domain"]
    assert len(config["themes"]) > 0


def test_themes_have_valid_slugs():
    """Theme slugs should be lowercase with hyphens only."""
    config = _load_yaml(os.path.join(FIXTURES, "sample_config.yaml"))
    import re
    for theme in config["themes"]:
        assert re.match(r"^[a-z0-9-]+$", theme["slug"]), f"Invalid slug: {theme['slug']}"


def test_themes_have_keywords():
    """Every theme must have at least one keyword."""
    config = _load_yaml(os.path.join(FIXTURES, "sample_config.yaml"))
    for theme in config["themes"]:
        assert len(theme["keywords"]) > 0, f"Theme {theme['slug']} has no keywords"


def test_config_has_at_least_one_source():
    """Config must have at least one RSS feed or Brave query."""
    config = _load_yaml(os.path.join(FIXTURES, "sample_config.yaml"))
    feeds = config.get("discovery", {}).get("rss_feeds", [])
    queries = config.get("discovery", {}).get("brave_queries", [])
    has_feeds = any(f.get("url") for f in feeds)
    has_queries = len(queries) > 0
    assert has_feeds or has_queries


# ─── audience + first_principles validation ─────────────────────────────────


def test_validate_passes_without_audience_or_principles():
    """Both blocks are optional — config should validate without them."""
    _validate(_base_config())  # should not raise/exit


def test_validate_accepts_valid_audience():
    config = _base_config()
    config["audience"] = {
        "description": "test readers",
        "knows_already": "basics",
        "cares_about": "outcomes",
    }
    _validate(config)


def test_validate_rejects_non_dict_audience():
    config = _base_config()
    config["audience"] = "a string, not a dict"
    with pytest.raises(SystemExit):
        _validate(config)


def test_validate_rejects_non_string_audience_field():
    config = _base_config()
    config["audience"] = {"description": 123}
    with pytest.raises(SystemExit):
        _validate(config)


def test_validate_accepts_valid_first_principles():
    config = _base_config()
    config["first_principles"] = [
        {"belief": "A is true."},
        {"belief": "B is true.", "post_url": "https://example.com/b", "post_title": "Why B"},
    ]
    _validate(config)


def test_validate_rejects_principle_without_belief():
    config = _base_config()
    config["first_principles"] = [{"post_url": "https://example.com"}]
    with pytest.raises(SystemExit):
        _validate(config)


def test_validate_rejects_principle_url_without_title():
    config = _base_config()
    config["first_principles"] = [{"belief": "X", "post_url": "https://example.com/x"}]
    with pytest.raises(SystemExit):
        _validate(config)


def test_validate_rejects_malformed_principle_url():
    config = _base_config()
    config["first_principles"] = [
        {"belief": "X", "post_url": "example.com/x", "post_title": "X"}
    ]
    with pytest.raises(SystemExit):
        _validate(config)


def test_validate_rejects_non_list_first_principles():
    config = _base_config()
    config["first_principles"] = {"belief": "X"}
    with pytest.raises(SystemExit):
        _validate(config)
