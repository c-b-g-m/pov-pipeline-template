#!/usr/bin/env python3
"""
POV Pipeline — Automated opinion content from industry news

Discovers articles via RSS/search, drafts opinion takes via Claude API,
and creates GitHub PRs for review. Social posting (e.g. LinkedIn via Buffer)
happens post-merge via a separate GitHub Action on your site repo.

Usage:
  python3 -m pipeline.main                 # Full run
  python3 -m pipeline.main --dry-run       # Discovery + draft, no PR/push
  python3 -m pipeline.main --discover-only # Discovery only, print candidates
  python3 -m pipeline.main --validate      # Check config, env, prerequisites; no API calls

Required environment variables (in .env or .env.local):
  ANTHROPIC_API_KEY     Claude API key
  SITE_REPO_PATH        Absolute path to your site's git repo

Optional:
  BRAVE_SEARCH_API_KEY  Enables Brave Web Search for broader discovery
  FIRECRAWL_API_KEY     Enables full article scraping for better drafts
  MAX_CANDIDATES        Override config max_candidates (default from config.yaml)
  RATE_LIMIT_SLEEP      Override config rate_limit_sleep (default from config.yaml)
"""

import argparse
import logging
import os
import shutil
import subprocess
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
from .publisher import create_pr, create_manifest_pr

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


def validate(config_path: str = None) -> list:
    """
    Pre-flight check: verify config, env vars, and prerequisites are in place
    before running the pipeline. Returns a list of human-readable error strings;
    an empty list means everything passed. Does not call any paid APIs.

    Checks:
      - config.yaml loads and passes schema validation
      - ANTHROPIC_API_KEY is set
      - voice-guidelines.md exists
      - SITE_REPO_PATH is set and points to an existing directory
      - site.content_path (from config) exists inside SITE_REPO_PATH
      - `gh` CLI is installed and authenticated
    """
    from .drafter import VOICE_GUIDELINES_PATH

    errors = []

    try:
        config = load_config(config_path)
    except SystemExit:
        errors.append("config.yaml failed to load — see log output above for details")
        return errors

    if not os.environ.get("ANTHROPIC_API_KEY"):
        errors.append("ANTHROPIC_API_KEY is not set (add it to .env.local or .env)")

    if not os.path.exists(VOICE_GUIDELINES_PATH):
        errors.append(
            f"voice-guidelines.md not found at {VOICE_GUIDELINES_PATH} "
            "(copy voice-guidelines.example.md to voice-guidelines.md and customize)"
        )

    site_repo_path = os.environ.get("SITE_REPO_PATH", "")
    if not site_repo_path:
        errors.append("SITE_REPO_PATH is not set (add it to .env.local or .env)")
    elif not os.path.isdir(site_repo_path):
        errors.append(f"SITE_REPO_PATH does not exist or is not a directory: {site_repo_path}")
    else:
        content_path = config.get("site", {}).get("content_path", "")
        if content_path:
            full_content_path = os.path.join(site_repo_path, content_path)
            if not os.path.isdir(full_content_path):
                errors.append(
                    f"site.content_path directory does not exist: {full_content_path} "
                    "(create it in your site repo before running the pipeline)"
                )

    if not shutil.which("gh"):
        errors.append(
            "`gh` CLI not found on PATH "
            "(install from https://cli.github.com, then run `gh auth login`)"
        )
    else:
        try:
            result = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                errors.append("`gh` CLI is installed but not authenticated (run `gh auth login`)")
        except (subprocess.TimeoutExpired, OSError) as e:
            errors.append(f"`gh auth status` check failed: {e}")

    return errors


def _run_validate(config_path: str = None) -> int:
    """CLI wrapper for validate() — prints results and returns exit code."""
    print("POV Pipeline — pre-flight validation")
    print("=" * 60)
    errors = validate(config_path)
    if errors:
        print(f"FAILED — {len(errors)} issue(s) found:\n")
        for i, err in enumerate(errors, 1):
            print(f"  {i}. {err}")
        print("\nFix the issues above, then re-run with --validate until it passes.")
        return 1
    print("OK — config, environment, and prerequisites all look good.")
    print("Ready to run: python3 -m pipeline.main --dry-run")
    return 0


def main():
    parser = argparse.ArgumentParser(description="POV Pipeline")
    parser.add_argument("--dry-run", action="store_true",
                        help="Discovery + draft, skip PR creation")
    parser.add_argument("--discover-only", action="store_true",
                        help="Run discovery only, print candidates")
    parser.add_argument("--validate", action="store_true",
                        help="Check config, env vars, and prerequisites; no API calls")
    parser.add_argument("--config", default=None,
                        help="Path to config.yaml (default: repo root)")
    args = parser.parse_args()

    if args.validate:
        sys.exit(_run_validate(args.config))

    # Load config
    config = load_config(args.config)
    _setup_logging(config)

    log = logging.getLogger(__name__)

    # Read env vars
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    site_repo_path = os.environ.get("SITE_REPO_PATH", "")
    brave_key = os.environ.get("BRAVE_SEARCH_API_KEY", "")
    firecrawl_key = os.environ.get("FIRECRAWL_API_KEY", "")
    rate_limit = float(os.environ.get(
        "RATE_LIMIT_SLEEP",
        config.get("pipeline", {}).get("rate_limit_sleep", 2)
    ))

    # MAX_CANDIDATES env override — applied to config before discovery reads it
    max_candidates_override = os.environ.get("MAX_CANDIDATES")
    if max_candidates_override:
        try:
            config.setdefault("discovery", {})["max_candidates"] = int(max_candidates_override)
        except ValueError:
            log.warning("MAX_CANDIDATES env var is not an integer: %r — ignoring", max_candidates_override)

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

    # Warn if Brave queries are configured but the API key is missing — they'll silently return no results
    brave_queries = config.get("discovery", {}).get("brave_queries", [])
    if brave_queries and not brave_key:
        log.warning(
            "config has %d brave_queries but BRAVE_SEARCH_API_KEY is not set. "
            "These queries will return zero results. Set the key in .env.local or remove brave_queries from config.yaml.",
            len(brave_queries),
        )

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
    drafts_with_urls = []  # [(draft_dict, source_url), ...]

    for candidate in candidates:
        draft = draft_take(candidate, config, anthropic_key, firecrawl_key)
        if draft:
            drafts_with_urls.append((draft, candidate["url"]))
            log.info("  Drafted: %s", draft["slug"])
        else:
            log.warning("  Failed to draft: %s", candidate["title"][:60])

        time.sleep(rate_limit)

    if not drafts_with_urls:
        log.info("No drafts produced. Nothing to publish.")
        return

    log.info("Produced %d drafts", len(drafts_with_urls))

    if args.dry_run:
        log.info("[DRY RUN] Drafts produced but not published.")
        for draft, _ in drafts_with_urls:
            log.info("  - %s (%s)", draft["slug"], draft["metadata"]["theme"])
            log.info("    Description: %s", draft["metadata"]["description"][:100])
        mark_processed([url for _, url in drafts_with_urls])
        return

    # ─── Step 3: Create PRs ──────────────────────────────────────────────
    log.info("Step 3: Creating GitHub PRs")
    pr_urls = []
    published_urls = []

    for draft, source_url in drafts_with_urls:
        pr_url = create_pr(draft, config, site_repo_path)
        if pr_url:
            pr_urls.append(pr_url)
            published_urls.append(source_url)
            log.info("  PR created: %s", pr_url)
        else:
            log.error("  Failed to create PR for: %s — will retry on next run", draft["slug"])

    # ─── Step 4: Manifest PR (HTML output only) ──────────────────────────
    manifest_url = None
    drafts = [draft for draft, _ in drafts_with_urls]
    output_format = config.get("drafting", {}).get("output_format", "mdx")
    if output_format == "html" and drafts:
        log.info("Step 4: Creating manifest PR (posts.json)")
        manifest_url = create_manifest_pr(drafts, config, site_repo_path)
        if manifest_url:
            log.info("  Manifest PR: %s", manifest_url)
        else:
            log.warning("  Manifest PR not created — posts.json will need manual update")

    mark_processed(published_urls)

    # ─── Summary ─────────────────────────────────────────────────────────
    log.info("=" * 60)
    log.info("Pipeline complete")
    log.info("  Candidates found: %d", len(candidates))
    log.info("  Drafts produced:  %d", len(drafts_with_urls))
    log.info("  PRs created:      %d", len(pr_urls))
    if pr_urls:
        log.info("  Article PRs (merge these first, in any order):")
        for url in pr_urls:
            log.info("    %s", url)
    if manifest_url:
        log.info("  Manifest PR (merge this last):")
        log.info("    %s", manifest_url)
    log.info("=" * 60)


if __name__ == "__main__":
    main()
