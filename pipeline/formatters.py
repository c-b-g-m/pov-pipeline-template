"""
Output formatters — build the final content file from draft data.

Supports MDX and Markdown output formats. The format is selected
via config.yaml: drafting.output_format
"""

import logging
from datetime import datetime
from typing import Callable

log = logging.getLogger(__name__)


def format_mdx(draft_data: dict, config: dict) -> tuple:
    """Format draft as MDX with YAML frontmatter. Returns (content, filename)."""
    content = _build_content(draft_data)
    filename = f"{draft_data['slug']}.mdx"
    return content, filename


def format_markdown(draft_data: dict, config: dict) -> tuple:
    """Format draft as Markdown with YAML frontmatter. Returns (content, filename)."""
    content = _build_content(draft_data)
    filename = f"{draft_data['slug']}.md"
    return content, filename


def _build_content(draft_data: dict) -> str:
    """Build the file content with frontmatter and body."""
    meta = draft_data["metadata"]

    safe_title = meta["title"].replace('"', '\\"')
    safe_description = meta["description"].replace('"', '\\"')
    safe_source_title = meta["title"].replace('"', '\\"')

    linkedin_draft = draft_data.get("linkedin_draft", "")
    linkedin_escaped = linkedin_draft.replace('"', '\\"').replace("\n", "\\n") if linkedin_draft else ""

    tags_str = ", ".join(f'"{t}"' for t in meta.get("tags", []))

    content = f'''---
title: "{safe_title}"
description: "{safe_description}"
sourceUrl: "{meta['source_url']}"
sourceTitle: "{safe_source_title}"
publishDate: {meta.get('publish_date', '')}
theme: "{meta['theme']}"
tags: [{tags_str}]
featured: false
linkedInDraft: "{linkedin_escaped}"
---

{draft_data['site_draft']}
'''
    return content


def get_formatter(config: dict) -> Callable:
    """Return the appropriate formatter function based on config."""
    fmt = config.get("drafting", {}).get("output_format", "mdx")
    if fmt == "markdown":
        return format_markdown
    return format_mdx
