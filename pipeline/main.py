#!/usr/bin/env python3
"""
POV Pipeline — Automated opinion content from industry news

Discovers articles via RSS/search, drafts opinion takes via Claude API,
creates GitHub PRs for review, and optionally queues social posts in Buffer.

Usage:
  python3 -m pipeline.main                 # Full run
  python3 -m pipeline.main --dry-run       # Discovery + draft, no PR/push/Buffer
  python3 -m pipeline.main --discover-only # Discovery only, print candidates

Required environment variables (in .env or .env.local):
  ANTHROPIC_API_KEY     Claude API key
  SITE_REPO_PATH        Absolute path to your site's git repo

Optional:
  BRAVE_SEARCH_API_KEY  Enables Brave Web Search for broader discovery
  FIRECRAWL_API_KEY     Enables full article scraping for better drafts
  BUFFER_ACCESS_TOKEN   Enables Buffer social draft posting
  MAX_CANDIDATES        Override config max_candidates (default from config.yaml)
  RATE_LIMIT_SLEEP      Override config rate_limit_sleep (default from config.yaml)
"""

import argparse
import logging
import os
import sys
import time

from dotenv import load_dotenv

# Load .env.local first, fall back to .env
_base = os.path.dirname(os.path.dirname(__file__))
env_local = os.path.join(_base, ".env.local")
env_file = os.path.join(_base, ".env")
load_dotenv(dotenv_path=env_local if os.path.exists(env_local) else env_file)

from .config_loader import load_config
from .discovery import discover, mark_processed
from .drafter import draft_take
from .publisher import create_pr
from .buffer_client import send_to_buffer

# ─── Logging ──────────────────────────────────────────────────────────────────


def _setup_logging(config: dict):
    log_file = config.get("pipeline", {}).get("log_file", "pipeline.log")
    log_path = os.path.join(_base, log_file)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_path, encoding="utf-8"),
        ],
    )


def main():
    parser = argparse.ArgumentParser(description="POV Pipeline")
    parser.add_argument("--dry-run", action="store_true",
                        help="Discovery + draft, skip PR creation and Buffer")
    parser.add_argument("--discover-only", action="store_true",
                        help="Run discovery only, print candidates")
    parser.add_argument("--config", default=None,
                        help="Path to config.yaml (default: repo root)")
    args = parser.parse_args()

    # Load config
    config = load_config(args.config)
    _setup_logging(config)

    log = logging.getLogger(__name__)

    # Read env vars
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    site_repo_path = os.environ.get("SITE_REPO_PATH", "")
    brave_key = os.environ.get("BRAVE_SEARCH_API_KEY", "")
    buffer_token = os.environ.get("BUFFER_ACCESS_TOKEN", "")
    firecrawl_key = os.environ.get("FIRECRAWL_API_KEY", "")
    rate_limit = float(os.environ.get(
        "RATE_LIMIT_SLEEP",
        config.get("pipeline", {}).get("rate_limit_sleep", 2)
    ))

    log.info("=" * 60)
    log.info("POV Pipeline — starting run")
    log.info("  Author: %s", config["author"]["name"])
    log.info("  Industry: %s", config["author"]["specialization"])
    log.info("=" * 60)

    # ─── Validate ────────────────────────────────────────────────────────
    if not args.discover_only and not anthropic_key:
        log.critical("ANTHROPIC_API_KEY is required for drafting. Set it in .env or .env.local")
        sys.exit(1)

    if not args.discover_only and not args.dry_run and not site_repo_path:
        log.critical("SITE_REPO_PATH is required for PR creation. Set it in .env or .env.local")
        sys.exit(1)

    if not args.dry_run and not args.discover_only and site_repo_path and not os.path.isdir(site_repo_path):
        log.critical("SITE_REPO_PATH does not exist: %s", site_repo_path)
        sys.exit(1)

    # ─── Step 1: Discovery ───────────────────────────────────────────────
    log.info("Step 1: Discovery")
    candidates = discover(config, brave_api_key=brave_key)

    if not candidates:
        log.info("No candidates found. Nothing to do.")
        return

    log.info("Found %d candidates:", len(candidates))
    for i, c in enumerate(candidates, 1):
        log.info("  %d. [%s] %s", i, c.get("theme", "unthemed"), c["title"][:70])
        log.info("     %s", c["url"])

    if args.discover_only:
        log.info("Discovery-only mode — done.")
        return

    # ─── Step 2: Drafting ────────────────────────────────────────────────
    log.info("Step 2: Drafting via Claude API")
    drafts = []
    processed_urls = []

    for candidate in candidates:
        draft = draft_take(candidate, config, anthropic_key, firecrawl_key)
        if draft:
            drafts.append(draft)
            processed_urls.append(candidate["url"])
            log.info("  Drafted: %s", draft["slug"])
        else:
            log.warning("  Failed to draft: %s", candidate["title"][:60])

        time.sleep(rate_limit)

    if not drafts:
        log.info("No drafts produced. Nothing to publish.")
        mark_processed(processed_urls)
        return

    log.info("Produced %d drafts", len(drafts))

    if args.dry_run:
        log.info("[DRY RUN] Drafts produced but not published.")
        for d in drafts:
            log.info("  - %s (%s)", d["slug"], d["metadata"]["theme"])
            log.info("    Description: %s", d["metadata"]["description"][:100])
        mark_processed(processed_urls)
        return

    # ─── Step 3: Create PRs ──────────────────────────────────────────────
    log.info("Step 3: Creating GitHub PRs")
    pr_urls = []
    site_domain = config.get("site", {}).get("domain", "")
    url_pattern = config.get("site", {}).get("url_pattern", "/pov/{slug}/")

    for draft in drafts:
        pr_url = create_pr(draft, config, site_repo_path)
        if pr_url:
            pr_urls.append(pr_url)
            log.info("  PR created: %s", pr_url)

            # ─── Step 4: Buffer ──────────────────────────────────────
            buffer_cfg = config.get("buffer", {})
            if buffer_token and buffer_cfg.get("enabled", False):
                site_url = f"https://{site_domain}{url_pattern.format(slug=draft['slug'])}"
                sent = send_to_buffer(
                    access_token=buffer_token,
                    social_draft=draft.get("linkedin_draft", ""),
                    site_url=site_url,
                )
                if sent:
                    log.info("  Buffer draft queued")
                else:
                    log.warning("  Buffer draft failed — post manually")
        else:
            log.error("  Failed to create PR for: %s", draft["slug"])

    mark_processed(processed_urls)

    # ─── Summary ─────────────────────────────────────────────────────────
    log.info("=" * 60)
    log.info("Pipeline complete")
    log.info("  Candidates found: %d", len(candidates))
    log.info("  Drafts produced:  %d", len(drafts))
    log.info("  PRs created:      %d", len(pr_urls))
    if pr_urls:
        log.info("  PR URLs:")
        for url in pr_urls:
            log.info("    %s", url)
    log.info("=" * 60)


if __name__ == "__main__":
    main()
