"""Tests for config_loader module."""

import os
import pytest
import yaml

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


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
