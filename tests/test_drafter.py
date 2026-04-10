"""Tests for drafter module."""

import os
import pytest
import yaml
import pytz

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def _load_config():
    with open(os.path.join(FIXTURES, "sample_config.yaml"), "r") as f:
        return yaml.safe_load(f)


def _load_fixture(name):
    with open(os.path.join(FIXTURES, name), "r") as f:
        return f.read()


def test_slugify():
    from pipeline.drafter import _slugify
    assert _slugify("Hello World!") == "hello-world"
    assert _slugify("This is a Test -- with dashes") == "this-is-a-test-with-dashes"
    assert _slugify("  Leading and trailing  ") == "leading-and-trailing"
    assert len(_slugify("A" * 200)) <= 80


def test_parse_draft_response():
    from pipeline.drafter import _parse_draft_response
    config = _load_config()
    tz = pytz.UTC
    response_text = _load_fixture("sample_draft_response.txt")

    candidate = {
        "url": "https://example.com/article",
        "title": "Test Article Title",
        "theme": "theme-one",
        "summary": "A test summary.",
    }

    result = _parse_draft_response(response_text, candidate, config, tz)

    assert result is not None
    assert result["slug"] == "test-article-title"
    assert result["metadata"]["theme"] == "theme-one"
    assert result["metadata"]["description"] == "A bold take on why the industry is getting this wrong."
    assert len(result["metadata"]["tags"]) == 3
    assert "## The news" in result["site_draft"]
    assert "## My take" in result["site_draft"]
    assert result["linkedin_draft"]
    assert "[LINK]" in result["linkedin_draft"]


def test_build_system_prompt_contains_author():
    from pipeline.drafter import _build_system_prompt
    config = _load_config()
    prompt = _build_system_prompt(config)

    assert "Test Author" in prompt
    assert "test role" in prompt
    assert "test industry" in prompt
    assert "theme-one" in prompt
    assert "theme-two" in prompt


def test_build_system_prompt_contains_sections():
    from pipeline.drafter import _build_system_prompt
    config = _load_config()
    prompt = _build_system_prompt(config)

    assert "The news" in prompt
    assert "My take" in prompt
    assert "The so-what" in prompt


def test_build_system_prompt_includes_audience_when_present():
    from pipeline.drafter import _build_system_prompt
    config = _load_config()
    prompt = _build_system_prompt(config)

    assert "## Audience" in prompt
    assert "Test readers who care about test things" in prompt
    assert "Test basics" in prompt
    assert "Test outcomes" in prompt


def test_build_system_prompt_omits_audience_when_absent():
    from pipeline.drafter import _build_system_prompt
    config = _load_config()
    del config["audience"]
    prompt = _build_system_prompt(config)

    assert "## Audience" not in prompt


def test_build_system_prompt_includes_first_principles_when_present():
    from pipeline.drafter import _build_system_prompt
    config = _load_config()
    prompt = _build_system_prompt(config)

    assert "## First Principles" in prompt
    assert "Testing is non-negotiable." in prompt
    assert "Simple is better than clever." in prompt
    # Linked principle renders its markdown link
    assert "[Why tests matter](https://example.com/why-tests)" in prompt
    # Unlinked principle has no link markup
    assert "Explanatory post" in prompt  # at least one principle does


def test_build_system_prompt_omits_first_principles_when_absent():
    from pipeline.drafter import _build_system_prompt
    config = _load_config()
    del config["first_principles"]
    prompt = _build_system_prompt(config)

    assert "## First Principles" not in prompt
