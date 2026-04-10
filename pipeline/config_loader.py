"""
Config loader — reads and validates config.yaml.

All pipeline modules receive the config dict rather than reading
hardcoded values. This is what makes the pipeline industry-agnostic.
"""

import logging
import os
import sys

import yaml

log = logging.getLogger(__name__)

_CONFIG_CACHE = None


def load_config(path: str = None) -> dict:
    """Load config.yaml and validate required fields."""
    global _CONFIG_CACHE
    if _CONFIG_CACHE is not None:
        return _CONFIG_CACHE

    if path is None:
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")

    if not os.path.exists(path):
        log.critical(
            "config.yaml not found at %s\n"
            "Copy config.example.yaml to config.yaml and fill in your values.\n"
            "See README.md for setup instructions.",
            path,
        )
        sys.exit(1)

    try:
        with open(path, "r") as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        log.critical(
            "config.yaml contains invalid YAML.\n"
            "  %s\n"
            "Check indentation and syntax. See config.example.yaml for a working example.",
            e,
        )
        sys.exit(1)

    if not isinstance(config, dict):
        log.critical(
            "config.yaml is empty or not a YAML mapping.\n"
            "See config.example.yaml for a complete working example."
        )
        sys.exit(1)

    _validate(config)
    _CONFIG_CACHE = config
    return config


def _validate(config: dict):
    """Check that required fields are present and non-empty."""
    errors = []

    # Author
    author = config.get("author", {})
    if not author.get("name"):
        errors.append("author.name is required")
    if not author.get("role"):
        errors.append("author.role is required")
    if not author.get("specialization"):
        errors.append("author.specialization is required")

    # Site
    site = config.get("site", {})
    if not site.get("domain"):
        errors.append("site.domain is required")
    if not site.get("content_path"):
        errors.append("site.content_path is required")

    # Discovery — need at least one source
    discovery = config.get("discovery", {})
    feeds = discovery.get("rss_feeds", [])
    queries = discovery.get("brave_queries", [])
    has_feeds = any(f.get("url") for f in feeds)
    has_queries = len(queries) > 0
    if not has_feeds and not has_queries:
        errors.append("discovery: at least one rss_feed or brave_query is required")

    # Themes — need at least one
    themes = config.get("themes", [])
    if not themes:
        errors.append("themes: at least one theme is required")
    for i, theme in enumerate(themes):
        if not theme.get("slug"):
            errors.append(f"themes[{i}].slug is required")
        if not theme.get("keywords"):
            errors.append(f"themes[{i}].keywords is required (need at least one keyword)")

    # Audience — optional block. If present, must be a dict of string fields.
    audience = config.get("audience")
    if audience is not None:
        if not isinstance(audience, dict):
            errors.append("audience: must be a mapping with description/knows_already/cares_about fields")
        else:
            for field in ("description", "knows_already", "cares_about"):
                value = audience.get(field)
                if value is not None and not isinstance(value, str):
                    errors.append(f"audience.{field}: must be a string")

    # First principles — optional list. Each entry needs `belief`.
    # If `post_url` is set, `post_title` is required and url must start with http.
    principles = config.get("first_principles")
    if principles is not None:
        if not isinstance(principles, list):
            errors.append("first_principles: must be a list")
        else:
            for i, p in enumerate(principles):
                if not isinstance(p, dict):
                    errors.append(f"first_principles[{i}]: must be a mapping with a 'belief' field")
                    continue
                if not p.get("belief") or not isinstance(p.get("belief"), str):
                    errors.append(f"first_principles[{i}].belief: required, must be a non-empty string")
                if p.get("post_url"):
                    if not isinstance(p["post_url"], str) or not p["post_url"].startswith(("http://", "https://")):
                        errors.append(f"first_principles[{i}].post_url: must be a URL starting with http:// or https://")
                    if not p.get("post_title"):
                        errors.append(f"first_principles[{i}].post_title: required when post_url is set (link needs anchor text)")

    if errors:
        log.critical(
            "config.yaml validation failed:\n  - %s\n\n"
            "See config.example.yaml for a complete working example.",
            "\n  - ".join(errors),
        )
        sys.exit(1)


def get_theme_slugs(config: dict) -> list:
    """Return list of valid theme slugs from config."""
    return [t["slug"] for t in config.get("themes", [])]


def get_theme_keywords(config: dict) -> dict:
    """Return {slug: [keywords]} dict from config themes."""
    return {t["slug"]: t["keywords"] for t in config.get("themes", [])}


def get_theme_labels(config: dict) -> dict:
    """Return {slug: label} dict from config themes."""
    return {t["slug"]: t.get("label", t["slug"]) for t in config.get("themes", [])}
