"""
Discovery module — finds candidate articles for POV takes.

Sources:
  - RSS feeds (configured in config.yaml)
  - Brave Web Search API (optional, configured in config.yaml)

Returns a list of candidate dicts: {url, title, source, theme, summary}
"""

import json
import logging
import os
import re
import time
from datetime import datetime, timedelta
from typing import List, Optional
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import feedparser
import pytz

log = logging.getLogger(__name__)

# ─── State management ────────────────────────────────────────────────────────

STATE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "state", "processed_urls.json")


def _load_processed_urls() -> set:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return set(json.load(f))
    return set()


def _save_processed_urls(urls: set):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(sorted(urls), f, indent=2)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _normalize_url(url: str) -> str:
    p = urlparse(url)
    netloc = p.netloc[4:] if p.netloc.startswith("www.") else p.netloc
    path = p.path.rstrip("/") or "/"
    return f"{p.scheme}://{netloc}{path}"


def _is_blocked(url: str, blocked_domains: set) -> bool:
    domain = urlparse(url).netloc.replace("www.", "")
    return domain in blocked_domains


def _is_index_url(url: str) -> bool:
    path = urlparse(url).path
    if not path.strip("/"):
        return True
    if re.match(r"^/\d{4}(/\d{1,2}){0,2}/?$", path):
        return True
    return False


def _url_reachable(url: str, timeout: int = 10) -> bool:
    try:
        req = Request(url, method="HEAD", headers={"User-Agent": "POVPipelineBot/1.0"})
        with urlopen(req, timeout=timeout) as resp:
            return resp.status < 400
    except Exception:
        return False


def _matches_keywords(text: str, keywords: list) -> bool:
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in keywords)


def _detect_theme(text: str, theme_keywords: dict) -> Optional[str]:
    """Return the best-matching theme slug for the given text, or None."""
    best_theme = None
    best_count = 0
    text_lower = text.lower()
    for theme, keywords in theme_keywords.items():
        count = sum(1 for kw in keywords if kw.lower() in text_lower)
        if count > best_count:
            best_count = count
            best_theme = theme
    return best_theme if best_count > 0 else None


# ─── RSS Discovery ───────────────────────────────────────────────────────────

def discover_rss(config: dict) -> List[dict]:
    """Parse RSS feeds and return candidate articles."""
    discovery = config.get("discovery", {})
    tz = pytz.timezone(config.get("pipeline", {}).get("timezone", "UTC"))
    max_age_hours = discovery.get("max_article_age_hours", 72)
    cutoff = datetime.now(tz) - timedelta(hours=max_age_hours)

    feeds = discovery.get("rss_feeds", [])
    industry_keywords = discovery.get("industry_keywords", [])
    blocked = frozenset(discovery.get("blocked_domains", []))

    from .config_loader import get_theme_keywords
    theme_keywords = get_theme_keywords(config)

    candidates = []

    for feed_cfg in feeds:
        feed_url = feed_cfg.get("url", "")
        needs_filter = feed_cfg.get("needs_keyword_filter", False)

        if not feed_url:
            continue

        log.info("Parsing RSS: %s", feed_url)
        try:
            feed = feedparser.parse(feed_url)
        except Exception as e:
            log.warning("Failed to parse %s: %s", feed_url, e)
            continue

        for entry in feed.entries:
            title = entry.get("title", "")
            link = entry.get("link", "")
            summary = entry.get("summary", "")
            combined_text = f"{title} {summary}"

            if not link:
                continue

            if needs_filter and not _matches_keywords(combined_text, industry_keywords):
                continue

            theme = _detect_theme(combined_text, theme_keywords)

            url = _normalize_url(link)
            if _is_blocked(url, blocked) or _is_index_url(url):
                continue

            candidates.append({
                "url": url,
                "title": title.strip(),
                "source": urlparse(feed_url).netloc,
                "theme": theme,
                "summary": summary[:500] if summary else "",
            })

        log.info("  Found %d candidates from %s",
                 len([c for c in candidates if urlparse(feed_url).netloc in c["source"]]),
                 feed_url)

    return candidates


# ─── Brave Search Discovery ──────────────────────────────────────────────────

def discover_brave(config: dict, api_key: str) -> List[dict]:
    """Search Brave Web Search API for articles."""
    if not api_key:
        log.info("No BRAVE_SEARCH_API_KEY — skipping Brave discovery")
        return []

    discovery = config.get("discovery", {})
    queries = discovery.get("brave_queries", [])
    blocked = frozenset(discovery.get("blocked_domains", []))
    max_per_query = 5

    from .config_loader import get_theme_keywords
    theme_keywords = get_theme_keywords(config)

    candidates = []
    for query in queries:
        log.info("Brave search: %s", query[:60])
        try:
            from urllib.parse import quote_plus
            url = f"https://api.search.brave.com/res/v1/web/search?q={quote_plus(query)}&count={max_per_query}&freshness=pw"
            req = Request(url, headers={
                "Accept": "application/json",
                "X-Subscription-Token": api_key,
            })
            with urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())

            for result in data.get("web", {}).get("results", []):
                article_url = _normalize_url(result.get("url", ""))
                title = result.get("title", "")
                description = result.get("description", "")

                if _is_blocked(article_url, blocked) or _is_index_url(article_url):
                    continue

                theme = _detect_theme(f"{title} {description}", theme_keywords)

                candidates.append({
                    "url": article_url,
                    "title": title.strip(),
                    "source": "brave-search",
                    "theme": theme,
                    "summary": description[:500] if description else "",
                })

            time.sleep(1)
        except Exception as e:
            log.warning("Brave search failed for query: %s — %s", query[:40], e)
            continue

    return candidates


# ─── Main discovery function ─────────────────────────────────────────────────

def discover(config: dict, brave_api_key: str = "") -> List[dict]:
    """
    Run all discovery sources, deduplicate, filter already-processed URLs,
    and return the top candidates ranked by theme relevance.
    """
    discovery = config.get("discovery", {})
    max_candidates = discovery.get("max_candidates", 5)

    processed = _load_processed_urls()
    log.info("Loaded %d previously processed URLs", len(processed))

    rss_candidates = discover_rss(config)
    brave_candidates = discover_brave(config, brave_api_key)
    all_candidates = rss_candidates + brave_candidates

    # Deduplicate by normalized URL
    seen = set()
    unique = []
    for c in all_candidates:
        if c["url"] not in seen and c["url"] not in processed:
            seen.add(c["url"])
            unique.append(c)

    log.info("Discovery: %d total, %d unique, %d after dedup with history",
             len(all_candidates), len(seen), len(unique))

    # Check reachability for top candidates
    reachable = []
    for c in unique[:max_candidates * 3]:
        if _url_reachable(c["url"]):
            reachable.append(c)
        else:
            log.debug("Unreachable: %s", c["url"])
        if len(reachable) >= max_candidates * 2:
            break

    # Rank: articles with a detected theme score higher
    themed = [c for c in reachable if c.get("theme")]
    unthemed = [c for c in reachable if not c.get("theme")]
    ranked = themed + unthemed

    result = ranked[:max_candidates]
    log.info("Returning %d candidates for drafting", len(result))
    return result


def mark_processed(urls: List[str]):
    """Add URLs to the processed set so they aren't re-discovered."""
    processed = _load_processed_urls()
    processed.update(urls)
    _save_processed_urls(processed)
    log.info("Marked %d URLs as processed (total: %d)", len(urls), len(processed))
