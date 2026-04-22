"""
Output formatters — build the final content file from draft data.

Supports MDX, Markdown, and HTML output formats. The format is selected
via config.yaml: drafting.output_format
"""

import html as _html_lib
import json
import logging
import re
import yaml
from typing import Callable
from urllib.parse import urlparse

log = logging.getLogger(__name__)

# ─── Markdown → HTML ─────────────────────────────────────────────────────────

def _apply_inline(text: str) -> str:
    """Apply inline markdown: links, bold, italic."""
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)',
                  r'<a href="\2" target="_blank" rel="noopener">\1</a>', text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', text)
    return text


def _md_to_html(text: str) -> str:
    """Convert simple markdown (headings, bold, links, paragraphs, lists) to HTML."""
    blocks = re.split(r'\n{2,}', text.strip())
    parts = []

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        if block.startswith('## '):
            parts.append(f'<h2>{_apply_inline(block[3:].strip())}</h2>')
        elif block.startswith('### '):
            parts.append(f'<h3>{_apply_inline(block[4:].strip())}</h3>')
        elif re.match(r'^[-*] ', block):
            lines = block.split('\n')
            items = []
            for line in lines:
                line = line.strip()
                if re.match(r'^[-*] ', line):
                    items.append(f'<li>{_apply_inline(line[2:])}</li>')
            parts.append('<ul>\n' + '\n'.join(items) + '\n</ul>')
        else:
            para = _apply_inline(block.replace('\n', ' '))
            parts.append(f'<p>{para}</p>')

    return '\n'.join(parts)


# ─── HTML formatter ───────────────────────────────────────────────────────────

_FAVICON = (
    "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'>"
    "<defs><linearGradient id='g' x1='0%25' y1='0%25' x2='100%25' y2='100%25'>"
    "<stop offset='0%25' style='stop-color:%23A07AFF'/>"
    "<stop offset='100%25' style='stop-color:%2300DCB4'/></linearGradient></defs>"
    "<polygon points='18,2 6,18 14,18 13,30 26,14 18,14' fill='url(%23g)'/></svg>"
)


def _get_theme_label(theme_slug: str, config: dict) -> str:
    for t in config.get("themes", []):
        if t["slug"] == theme_slug:
            return t.get("label", theme_slug)
    return theme_slug


def format_html(draft_data: dict, config: dict) -> tuple:
    """Format draft as a full HTML page for a static site. Returns (content, filename).

    Required config.yaml fields:
      site.domain  — root domain without protocol, e.g. "mysite.com"
      site.name    — display name used in page titles, nav, and footer

    Optional config.yaml fields:
      site.og_image      — OG image path (site-relative) or absolute URL.
                           Defaults to /og-images/og-pov-default.png — you must
                           provide this file in your site repo.
      site.cta           — CTA block rendered below the article body. Omit the
                           entire key to suppress the section.
        site.cta.heading   — section heading text
        site.cta.body      — paragraph copy
        site.cta.link_url  — button destination URL
        site.cta.link_text — button label

    The template links /shared.css for CSS variables and base styles.
    You must provide this stylesheet in your site repo's root.
    """
    meta = draft_data["metadata"]
    site = config.get("site", {})

    slug = draft_data["slug"]
    domain = site.get("domain", "")
    site_name = site.get("name", domain)
    author_name = config.get("author", {}).get("name", site_name)
    url = f"https://{domain}/pov/{slug}/"

    title_safe = _html_lib.escape(meta["title"])
    desc_safe = _html_lib.escape(meta["description"])
    site_name_safe = _html_lib.escape(site_name)
    theme_label = _get_theme_label(meta["theme"], config)
    publish_date = meta.get("publish_date", "")
    source_url = meta.get("source_url", "")
    source_host = urlparse(source_url).netloc.lstrip("www.") if source_url else ""
    source_title = _html_lib.escape(source_host or source_url)
    tags = meta.get("tags", [])

    og_image_path = site.get("og_image", "/og-images/og-pov-default.png")
    og_image_url = og_image_path if og_image_path.startswith("http") else f"https://{domain}{og_image_path}"

    body_html = _md_to_html(draft_data["site_draft"])

    # ── JSON-LD ──
    ld_article = json.dumps({
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": meta["title"],
        "description": meta["description"],
        "datePublished": publish_date,
        "author": {
            "@type": "Organization",
            "name": author_name,
            "url": f"https://{domain}"
        },
        "publisher": {
            "@type": "Organization",
            "name": author_name,
            "url": f"https://{domain}"
        },
        "url": url,
        "keywords": tags,
    }, indent=2)

    ld_breadcrumb = json.dumps({
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": f"https://{domain}/"},
            {"@type": "ListItem", "position": 2, "name": "POV", "item": f"https://{domain}/pov/"},
            {"@type": "ListItem", "position": 3, "name": meta["title"], "item": url},
        ]
    }, indent=2)

    # ── CSS ──
    styles = """
<style>
.pov-header {
  position: relative;
  z-index: 10;
  max-width: 720px;
  margin: 0 auto;
  padding: 72px 56px 40px;
}
.pov-eyebrow {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}
.pov-theme {
  font-family: 'Syne', sans-serif;
  font-weight: 700;
  font-size: 10px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--teal-dim);
  border: 1px solid rgba(0,220,180,0.25);
  padding: 4px 10px;
}
.pov-date {
  font-size: 13px;
  color: var(--muted);
}
h1.pov-title {
  font-family: 'Fraunces', serif;
  font-size: clamp(28px, 4vw, 52px);
  font-weight: 300;
  font-variation-settings: 'opsz' 144;
  letter-spacing: -0.02em;
  color: var(--cream);
  line-height: 1.15;
  margin-bottom: 20px;
}
.pov-description {
  font-size: 17px;
  color: var(--cream-dim);
  line-height: 1.7;
  margin-bottom: 24px;
  max-width: 600px;
}
.pov-source {
  font-size: 13px;
  color: var(--muted);
}
.pov-source a {
  color: var(--teal-dim);
  text-decoration: none;
  border-bottom: 1px solid rgba(0,220,180,0.3);
  transition: color 0.2s, border-color 0.2s;
}
.pov-source a:hover {
  color: var(--teal);
  border-bottom-color: var(--teal);
}
.pov-body {
  position: relative;
  z-index: 10;
  max-width: 720px;
  margin: 0 auto;
  padding: 0 56px 80px;
}
.pov-body h2 {
  font-family: 'Syne', sans-serif;
  font-weight: 700;
  font-size: 10px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--violet-dim);
  margin: 48px 0 16px;
  padding-top: 48px;
  border-top: 1px solid var(--border-2);
}
.pov-body h2:first-child {
  margin-top: 0;
  padding-top: 0;
  border-top: none;
}
.pov-body h3 {
  font-family: 'Fraunces', serif;
  font-size: 18px;
  font-weight: 600;
  font-variation-settings: 'opsz' 36;
  color: var(--cream);
  margin: 24px 0 12px;
}
.pov-body p {
  font-size: 16px;
  color: var(--cream-dim);
  line-height: 1.85;
  margin-bottom: 20px;
}
.pov-body strong {
  color: var(--cream);
  font-weight: 500;
}
.pov-body a {
  color: var(--teal-dim);
  text-decoration: none;
  border-bottom: 1px solid rgba(0,220,180,0.3);
  transition: color 0.2s, border-color 0.2s;
}
.pov-body a:hover { color: var(--teal); border-bottom-color: var(--teal); }
.pov-body ul {
  list-style: none;
  padding: 0;
  margin-bottom: 20px;
}
.pov-body ul li {
  font-size: 16px;
  color: var(--cream-dim);
  line-height: 1.85;
  padding-left: 24px;
  position: relative;
  margin-bottom: 8px;
}
.pov-body ul li::before {
  content: '—';
  position: absolute;
  left: 0;
  color: var(--violet-dim);
}
@media (max-width: 768px) {
  .pov-header, .pov-body { padding-left: 24px; padding-right: 24px; }
  h1.pov-title { font-size: clamp(26px, 7vw, 42px); }
}
</style>"""

    # ── Optional CTA block (omit site.cta from config to suppress) ──
    cta = site.get("cta", {})
    if cta:
        cta_html = f"""
<!-- CTA -->
<section class="services-cta">
  <div class="services-cta-card">
    <h3>{_html_lib.escape(cta.get("heading", ""))}</h3>
    <p>{_html_lib.escape(cta.get("body", ""))}</p>
    <a href="{cta.get("link_url", "#")}" class="services-cta-link" target="_blank">{_html_lib.escape(cta.get("link_text", "Get in touch"))}</a>
  </div>
</section>"""
    else:
        cta_html = ""

    html_out = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title_safe} — {site_name_safe}</title>
<meta name="description" content="{desc_safe}">
<link rel="canonical" href="{url}">

<meta property="og:type" content="article">
<meta property="og:url" content="{url}">
<meta property="og:title" content="{title_safe} — {site_name_safe}">
<meta property="og:description" content="{desc_safe}">
<meta property="og:image" content="{og_image_url}">

<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title_safe} — {site_name_safe}">
<meta name="twitter:description" content="{desc_safe}">
<meta name="twitter:image" content="{og_image_url}">

<link rel="icon" href="{_FAVICON}">

<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,600;1,9..144,300;1,9..144,500;1,9..144,600&family=Barlow:ital,wght@0,300;0,400;0,500;0,600;1,300;1,400&family=Syne:wght@700;800&display=swap" rel="stylesheet">

<link rel="stylesheet" href="/shared.css">
{styles}
<script type="application/ld+json">
{ld_breadcrumb}
</script>
<script type="application/ld+json">
{ld_article}
</script>
</head>
<body>

<!-- Aurora Background -->
<div id="aurora-wrap">
  <div class="a-layer a1"></div>
  <div class="a-layer a2"></div>
  <div class="a-layer a3"></div>
  <div class="a-arc"></div>
</div>

<!-- Nav -->
<div class="nav-bar">
  <a href="https://{domain}" class="nav-logo">{site_name_safe}</a>
  <a href="/pov" class="nav-back">&larr; All takes</a>
</div>

<!-- Article Header -->
<header class="pov-header">
  <div class="pov-eyebrow">
    <span class="pov-theme">{theme_label}</span>
    <span class="pov-date">{publish_date}</span>
  </div>
  <h1 class="pov-title">{title_safe}</h1>
  <p class="pov-description">{desc_safe}</p>
  <p class="pov-source">Source: <a href="{source_url}" target="_blank" rel="noopener">{source_title}</a></p>
</header>

<!-- Article Body -->
<article class="pov-body">
{body_html}
</article>
{cta_html}

<!-- Footer -->
<footer class="footer">
  <div class="footer-left">
    &copy; 2026 <a href="https://{domain}">{site_name_safe}</a>
  </div>
  <div>
    <a href="https://{domain}">{_html_lib.escape(domain)}</a>
  </div>
</footer>

</body>
</html>"""

    filename = f"{slug}/index.html"
    return html_out, filename


# ─── Posts manifest helper ────────────────────────────────────────────────────

def build_posts_entry(draft_data: dict) -> dict:
    """Build a posts.json entry from draft data."""
    meta = draft_data["metadata"]
    return {
        "slug": draft_data["slug"],
        "title": meta["title"],
        "description": meta["description"],
        "theme": meta["theme"],
        "tags": meta.get("tags", []),
        "publishDate": meta.get("publish_date", ""),
    }


# ─── MDX / Markdown formatters ────────────────────────────────────────────────

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
    meta = draft_data["metadata"]
    source_url = meta.get("source_url", "")
    source_host = urlparse(source_url).netloc.lstrip("www.") if source_url else ""

    fm = {
        "title": meta["title"],
        "description": meta.get("description", ""),
        "sourceUrl": source_url,
        "sourceTitle": source_host or source_url,
        "publishDate": meta.get("publish_date", ""),
        "theme": meta.get("theme", ""),
        "tags": meta.get("tags", []),
        "featured": False,
        "linkedInDraft": draft_data.get("linkedin_draft", ""),
    }

    fm_str = yaml.dump(fm, default_flow_style=False, allow_unicode=True, sort_keys=False)
    return f"---\n{fm_str}---\n\n{draft_data['site_draft']}\n"


# ─── Formatter registry ───────────────────────────────────────────────────────

def get_formatter(config: dict) -> Callable:
    """Return the appropriate formatter function based on config."""
    fmt = config.get("drafting", {}).get("output_format", "mdx")
    if fmt == "markdown":
        return format_markdown
    if fmt == "html":
        return format_html
    return format_mdx
