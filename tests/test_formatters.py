"""Tests for pipeline/formatters.py."""

import pytest
import yaml
from datetime import datetime

from pipeline.formatters import (
    _apply_inline,
    _md_to_html,
    _get_theme_label,
    build_posts_entry,
    format_mdx,
    format_markdown,
    format_html,
    get_formatter,
)


SAMPLE_DRAFT = {
    "slug": "ai-is-overused",
    "filename": "ai-is-overused/index.html",
    "content": "<html>body</html>",
    "site_draft": "## The Case\n\nEveryone says AI. Nobody means the same thing.\n\n- Point one\n- Point two",
    "linkedin_draft": "Hot take: AI is overused.",
    "metadata": {
        "title": "AI Is Overused",
        "description": "A take on the overuse of the term AI.",
        "theme": "strategy",
        "tags": ["ai", "strategy"],
        "source_url": "https://techcrunch.com/article",
        "publish_date": "2026-04-22",
    },
}

SAMPLE_CONFIG = {
    "author": {"name": "Jordan Rivera"},
    "site": {
        "domain": "jordanrivera.dev",
        "name": "Jordan Rivera",
        "content_path": "src/content/pov",
    },
    "themes": [
        {"slug": "strategy", "label": "Go-to-Market Strategy"},
    ],
    "drafting": {"output_format": "html"},
}


# ─── _apply_inline ────────────────────────────────────────────────────────────

def test_apply_inline_bold():
    assert _apply_inline("**bold text**") == "<strong>bold text</strong>"


def test_apply_inline_italic():
    assert _apply_inline("*italic text*") == "<em>italic text</em>"


def test_apply_inline_link():
    result = _apply_inline("[click here](https://example.com)")
    assert '<a href="https://example.com"' in result
    assert "click here" in result


def test_apply_inline_passthrough():
    assert _apply_inline("plain text") == "plain text"


# ─── _md_to_html ─────────────────────────────────────────────────────────────

def test_md_to_html_paragraph():
    result = _md_to_html("Just a paragraph.")
    assert "<p>Just a paragraph.</p>" in result


def test_md_to_html_h2():
    result = _md_to_html("## Section Heading")
    assert "<h2>Section Heading</h2>" in result


def test_md_to_html_h3():
    result = _md_to_html("### Sub-heading")
    assert "<h3>Sub-heading</h3>" in result


def test_md_to_html_list():
    result = _md_to_html("- Item one\n- Item two")
    assert "<ul>" in result
    assert "<li>Item one</li>" in result
    assert "<li>Item two</li>" in result


# ─── _get_theme_label ─────────────────────────────────────────────────────────

def test_get_theme_label_found():
    result = _get_theme_label("strategy", SAMPLE_CONFIG)
    assert result == "Go-to-Market Strategy"


def test_get_theme_label_not_found_returns_slug():
    result = _get_theme_label("unknown-slug", SAMPLE_CONFIG)
    assert result == "unknown-slug"


# ─── build_posts_entry ───────────────────────────────────────────────────────

def test_build_posts_entry_fields():
    entry = build_posts_entry(SAMPLE_DRAFT)
    assert entry["slug"] == "ai-is-overused"
    assert entry["title"] == "AI Is Overused"
    assert entry["description"] == "A take on the overuse of the term AI."
    assert entry["theme"] == "strategy"
    assert entry["tags"] == ["ai", "strategy"]
    assert entry["publishDate"] == "2026-04-22"


# ─── format_mdx / format_markdown ─────────────────────────────────────────────

def test_format_mdx_filename():
    _, filename = format_mdx(SAMPLE_DRAFT, SAMPLE_CONFIG)
    assert filename == "ai-is-overused.mdx"


def test_format_markdown_filename():
    _, filename = format_markdown(SAMPLE_DRAFT, SAMPLE_CONFIG)
    assert filename == "ai-is-overused.md"


def test_format_mdx_frontmatter_keys():
    content, _ = format_mdx(SAMPLE_DRAFT, SAMPLE_CONFIG)
    assert content.startswith("---\n")
    fm_text = content.split("---\n")[1]
    fm = yaml.safe_load(fm_text)
    assert fm["title"] == "AI Is Overused"
    assert fm["sourceUrl"] == "https://techcrunch.com/article"
    assert fm["sourceTitle"] == "techcrunch.com"
    assert fm["tags"] == ["ai", "strategy"]
    assert fm["featured"] is False


def test_format_mdx_body_follows_frontmatter():
    content, _ = format_mdx(SAMPLE_DRAFT, SAMPLE_CONFIG)
    parts = content.split("---\n")
    # parts[0]="", parts[1]=frontmatter, parts[2]="\n{body}"
    body = parts[2]
    assert "Everyone says AI" in body


def test_format_mdx_yaml_handles_colon_in_title():
    draft = {
        **SAMPLE_DRAFT,
        "metadata": {**SAMPLE_DRAFT["metadata"], "title": "AI: The Overused Term"},
    }
    content, _ = format_mdx(draft, SAMPLE_CONFIG)
    fm_text = content.split("---\n")[1]
    fm = yaml.safe_load(fm_text)
    assert fm["title"] == "AI: The Overused Term"


# ─── format_html ──────────────────────────────────────────────────────────────

def test_format_html_filename():
    _, filename = format_html(SAMPLE_DRAFT, SAMPLE_CONFIG)
    assert filename == "ai-is-overused/index.html"


def test_format_html_contains_title():
    html, _ = format_html(SAMPLE_DRAFT, SAMPLE_CONFIG)
    assert "AI Is Overused" in html


def test_format_html_og_image_absolute_url():
    config = {**SAMPLE_CONFIG, "site": {**SAMPLE_CONFIG["site"], "og_image": "/og-images/card.png"}}
    html, _ = format_html(SAMPLE_DRAFT, config)
    assert 'content="https://jordanrivera.dev/og-images/card.png"' in html


def test_format_html_og_image_already_absolute():
    config = {**SAMPLE_CONFIG, "site": {**SAMPLE_CONFIG["site"], "og_image": "https://cdn.example.com/card.png"}}
    html, _ = format_html(SAMPLE_DRAFT, config)
    assert 'content="https://cdn.example.com/card.png"' in html


def test_format_html_no_cta_when_absent():
    config = {**SAMPLE_CONFIG, "site": {k: v for k, v in SAMPLE_CONFIG["site"].items() if k != "cta"}}
    html, _ = format_html(SAMPLE_DRAFT, config)
    assert "services-cta" not in html


def test_format_html_cta_when_present():
    config = {
        **SAMPLE_CONFIG,
        "site": {
            **SAMPLE_CONFIG["site"],
            "cta": {
                "heading": "Work with me",
                "body": "Get in touch.",
                "link_url": "https://jordanrivera.dev/contact",
                "link_text": "Contact",
            },
        },
    }
    html, _ = format_html(SAMPLE_DRAFT, config)
    assert "services-cta" in html
    assert "Work with me" in html


def test_format_html_copyright_year_is_current():
    html, _ = format_html(SAMPLE_DRAFT, SAMPLE_CONFIG)
    assert f"&copy; {datetime.now().year}" in html


def test_format_html_source_domain_extracted():
    html, _ = format_html(SAMPLE_DRAFT, SAMPLE_CONFIG)
    assert "techcrunch.com" in html


def test_format_html_json_ld_keywords_is_array():
    import json as _json
    import re
    html, _ = format_html(SAMPLE_DRAFT, SAMPLE_CONFIG)
    ld_blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
    article_ld = next(b for b in ld_blocks if '"Article"' in b)
    parsed = _json.loads(article_ld)
    assert isinstance(parsed["keywords"], list)


# ─── get_formatter ────────────────────────────────────────────────────────────

def test_get_formatter_html():
    config = {"drafting": {"output_format": "html"}}
    assert get_formatter(config) is format_html


def test_get_formatter_markdown():
    config = {"drafting": {"output_format": "markdown"}}
    assert get_formatter(config) is format_markdown


def test_get_formatter_mdx_explicit():
    config = {"drafting": {"output_format": "mdx"}}
    assert get_formatter(config) is format_mdx


def test_get_formatter_default_is_mdx():
    assert get_formatter({}) is format_mdx
