"""
Drafting module — uses Claude API to generate POV takes from candidate articles.

For each candidate, produces:
  1. A content file (MDX or Markdown) for the user's site
  2. A social media post draft (stored in frontmatter)
"""

import logging
import os
import re
from datetime import datetime
from typing import Optional

import anthropic
import pytz

log = logging.getLogger(__name__)

VOICE_GUIDELINES_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "voice-guidelines.md"
)


def _load_voice_guidelines() -> str:
    if not os.path.exists(VOICE_GUIDELINES_PATH):
        log.warning(
            "voice-guidelines.md not found at %s. "
            "Copy voice-guidelines.example.md to voice-guidelines.md and customize it.",
            VOICE_GUIDELINES_PATH,
        )
        return ""
    with open(VOICE_GUIDELINES_PATH, "r") as f:
        return f.read()


def _scrape_article(url: str, api_key: str) -> Optional[str]:
    """Scrape full article content via Firecrawl. Returns markdown or None."""
    if not api_key:
        return None
    try:
        from firecrawl import FirecrawlApp
        app = FirecrawlApp(api_key=api_key)
        result = app.scrape(url, formats=["markdown"])
        markdown = result.get("markdown", "") if isinstance(result, dict) else getattr(result, "markdown", "")
        if markdown:
            return markdown[:3000]
        return None
    except Exception as e:
        log.warning("Firecrawl scrape failed for %s: %s", url, e)
        return None


def _slugify(title: str) -> str:
    slug = title.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    slug = slug.strip("-")
    return slug[:80]


def _build_audience_block(config: dict) -> str:
    """Build the audience framing block, or empty string if not configured."""
    audience = config.get("audience") or {}
    description = audience.get("description", "").strip()
    knows_already = audience.get("knows_already", "").strip()
    cares_about = audience.get("cares_about", "").strip()

    if not any([description, knows_already, cares_about]):
        return ""

    lines = ["## Audience", "", "You are writing for a specific reader. Calibrate vocabulary, assumed knowledge, and framing against them — do not write for a general audience.", ""]
    if description:
        lines.append(f"- Who they are: {description}")
    if knows_already:
        lines.append(f"- What they already know: {knows_already}")
    if cares_about:
        lines.append(f"- What they care about: {cares_about}")
    return "\n".join(lines) + "\n"


def _build_principles_block(config: dict) -> str:
    """Build the first-principles block, or empty string if not configured."""
    principles = config.get("first_principles") or []
    if not principles:
        return ""

    lines = []
    for p in principles:
        line = f"- {p['belief']}"
        if p.get("post_url") and p.get("post_title"):
            line += f'\n  Explanatory post: [{p["post_title"]}]({p["post_url"]})'
        lines.append(line)

    return (
        "## First Principles\n\n"
        "These are foundational beliefs you reason *from*. Never contradict them. "
        "When a principle is the crux of an argument — not just a passing reference — "
        "you may link to its explanatory post using standard markdown. Use at most one "
        "such link per take, and only when it genuinely helps a reader who wants to go "
        "deeper. Do not force a link.\n\n"
        + "\n".join(lines)
        + "\n"
    )


def _build_system_prompt(config: dict) -> str:
    """Build the system prompt dynamically from config values."""
    author = config["author"]["name"]
    role = config["author"]["role"]
    specialization = config["author"]["specialization"]

    audience_block = _build_audience_block(config)
    principles_block = _build_principles_block(config)

    # Build theme list
    themes = config.get("themes", [])
    theme_slugs = ", ".join(t["slug"] for t in themes)
    theme_descriptions = "\n".join(
        f"  - {t['slug']}: {t.get('description', t.get('label', t['slug']))}"
        for t in themes
    )

    # Build section instructions
    sections = config.get("drafting", {}).get("sections", [])
    section_instructions = "\n".join(
        f"- Start with ## {s['heading']}, then follow with the next sections"
        if i == 0 else f"- Then ## {s['heading']}"
        for i, s in enumerate(sections)
    )

    section_headings = " / ".join(f"## {s['heading']}" for s in sections)

    # Social draft config
    social = config.get("drafting", {}).get("social_draft", {})
    social_enabled = social.get("enabled", True)
    social_platform = social.get("platform", "linkedin")
    social_word_range = social.get("word_range", [150, 250])

    social_section = ""
    if social_enabled:
        social_section = f"""
--- {social_platform.upper()} DRAFT ---
A {social_platform.title()} post ({social_word_range[0]}-{social_word_range[1]} words) that:
- Opens with a hook that stops the scroll (not "I just published...")
- Delivers the sharpest insight from the take
- Ends with a line that drives clicks to the full piece
- Include "Link in comments" or a placeholder [LINK] at the end
- No hashtags
- Write in first person as {author}
"""

    return f"""\
You are a ghostwriter for {author}, a {role} specializing in {specialization}. \
Your job is to draft short opinion pieces ("POV takes") about {specialization} news \
for their website and {social_platform.title()}.

{audience_block}
{principles_block}
You will receive:
1. Voice guidelines that define their tone, POV, and structure
2. A source article URL, title, and summary
3. A suggested theme

You must produce TWO outputs, clearly separated:

--- SITE DRAFT ---
A content piece following the exact structure in the voice guidelines:
{section_instructions}
- Total body: 300-500 words
- Do NOT include frontmatter — that will be added programmatically
- Do NOT include an intro paragraph before the first section
- Write in first person as {author}
{social_section}
--- METADATA ---
- description: A 1-2 sentence hook for the piece (used in frontmatter and meta tags). Opinionated, not a summary.
- theme: One of: {theme_slugs}
  Themes:
{theme_descriptions}
- tags: 2-4 relevant keyword tags as a comma-separated list

Format your response EXACTLY as:
DESCRIPTION: <description text>
THEME: <theme-slug>
TAGS: <tag1>, <tag2>, <tag3>

--- SITE DRAFT ---
<content>

--- {social_platform.upper()} DRAFT ---
<{social_platform} post>
"""


def draft_take(candidate: dict, config: dict, api_key: str, firecrawl_key: str = "") -> Optional[dict]:
    """
    Generate a POV take for a single candidate article.

    Returns a dict with keys: slug, filename, site_draft, linkedin_draft, metadata
    Or None if drafting fails.
    """
    voice_guidelines = _load_voice_guidelines()
    system_prompt = _build_system_prompt(config)

    # Scrape full article content if Firecrawl is configured
    article_content = _scrape_article(candidate["url"], firecrawl_key)

    article_section = f"""- URL: {candidate['url']}
- Title: {candidate['title']}
- Summary: {candidate.get('summary', 'No summary available')}
- Suggested theme: {candidate.get('theme', 'Use your judgment based on the article content')}"""

    if article_content:
        article_section += f"""

### Full Article Content
{article_content}"""
        log.info("  Scraped full article (%d chars)", len(article_content))

    user_message = f"""\
## Voice Guidelines
{voice_guidelines}

## Source Article
{article_section}

Draft the POV take now, following the voice guidelines exactly."""

    model = config.get("drafting", {}).get("model", "claude-sonnet-4-6")
    max_tokens = config.get("drafting", {}).get("max_tokens", 2000)
    tz = pytz.timezone(config.get("pipeline", {}).get("timezone", "UTC"))

    client = anthropic.Anthropic(api_key=api_key)

    try:
        log.info("Drafting take for: %s", candidate["title"][:60])
        message = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )

        response_text = message.content[0].text
        return _parse_draft_response(response_text, candidate, config, tz)

    except Exception as e:
        log.error("Failed to draft take for %s: %s", candidate["url"], e)
        return None


def _parse_draft_response(text: str, candidate: dict, config: dict, tz) -> Optional[dict]:
    """Parse Claude's response into structured components."""
    from .config_loader import get_theme_slugs

    valid_themes = get_theme_slugs(config)

    # Extract metadata
    desc_match = re.search(r"DESCRIPTION:\s*(.+?)(?:\n|$)", text)
    theme_match = re.search(r"THEME:\s*(.+?)(?:\n|$)", text)
    tags_match = re.search(r"TAGS:\s*(.+?)(?:\n|$)", text)

    description = desc_match.group(1).strip() if desc_match else candidate.get("summary", "")[:200]

    theme = theme_match.group(1).strip() if theme_match else candidate.get("theme", "")
    if theme not in valid_themes:
        theme = valid_themes[0] if valid_themes else "general"

    tags_str = tags_match.group(1).strip() if tags_match else ""
    tags = [t.strip() for t in tags_str.split(",") if t.strip()]

    # Extract site draft
    site_match = re.search(r"---\s*SITE DRAFT\s*---\s*\n(.*?)(?=---\s*\w+\s*DRAFT\s*---|$)", text, re.DOTALL)
    site_draft = site_match.group(1).strip() if site_match else None

    # Extract social draft (platform-agnostic pattern)
    social_match = re.search(r"---\s*(?:LINKEDIN|SOCIAL)\s*DRAFT\s*---\s*\n(.*?)$", text, re.DOTALL)
    social_draft = social_match.group(1).strip() if social_match else None

    if not site_draft:
        log.error("Could not parse site draft from response")
        return None

    slug = _slugify(candidate["title"])
    today = datetime.now(tz).strftime("%Y-%m-%d")

    # Use the formatter to build the final content
    from .formatters import get_formatter
    formatter = get_formatter(config)

    draft_data = {
        "slug": slug,
        "site_draft": site_draft,
        "linkedin_draft": social_draft or "",
        "metadata": {
            "title": candidate["title"],
            "description": description,
            "theme": theme,
            "tags": tags,
            "source_url": candidate["url"],
            "publish_date": today,
        },
    }

    content, filename = formatter(draft_data, config)
    draft_data["content"] = content
    draft_data["filename"] = filename

    return draft_data
