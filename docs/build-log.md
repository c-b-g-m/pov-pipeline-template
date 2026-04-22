# Build Log — pov-pipeline-template

## Open bugs

None.

---

## 2026-04-22: Fix URL state management bug

**What was built:**
- `pipeline/main.py`: replaced parallel `drafts` + `processed_urls` lists with `drafts_with_urls` (paired tuples). PR creation loop now collects `published_urls` only on `create_pr()` success. `mark_processed()` called with `published_urls` instead of all drafted URLs — failed PRs are retried on the next run.
- `tests/test_main.py`: 5 new tests covering partial PR failure, full success, all-fail, dry-run (no `create_pr` called), and no-drafts-produced.

**What broke:** Nothing. 91/91 tests passing.

**Tech debt:** None introduced.

---

## 2026-04-22: Repo hardening and test coverage

**What was built:**
- Fork-readiness audit: 7 bugs and documentation gaps fixed (Social Draft naming, dead config fields, hardcoded copyright year, og_image README note, .env.local preference, state/.gitkeep, internal references scrubbed from docs)
- Test coverage added for `formatters.py`, `publisher.py`, and `buffer_client.py` — 47 new tests, 86 total passing
- LICENSE copyright attributed to demandAI studio
- `requirements.txt` split into runtime and dev (`requirements-dev.txt`)
- `CONTRIBUTING.md` added

**What broke:** Nothing.

**Tech debt:**
- URL state management bug (see Open bugs above) — deferred, architectural change needed in `main.py`

---

## 2026-04-21: Template Bug Fixes (public template hardening)

**What was built:**
- Audited template against a private fork and production integration to find bugs other users would hit
- `formatters.py` fully rewritten: PostHog removed entirely, `format_html()` made config-driven via `site.name` / `author.name` / `site.cta` / `site.og_image`, JSON-LD keywords fixed to array, YAML frontmatter switched to `yaml.dump()`, `sourceTitle` fixed to show source domain
- `publisher.py`: branch collision handling, commit/push failure cleanup
- `discovery.py`: `priority` and `max_per_feed` per-feed config + priority-aware ranking
- `config.example.yaml`: `site.name`, `og_image`, `cta` block, HTML output format docs, feed priority examples, Reddit blocking note
- All 19 commits in git history rewritten to scrub hardcoded PostHog key via `git filter-repo --replace-text`

**What broke:**
- Nothing in current functionality — all changes are backwards-compatible for existing users except `format_html()` now requires `site.name` in config (previously defaulted to a hardcoded value)

**Tech debt:**
- `sourceTitle` now shows source domain (e.g., `techcrunch.com`) but not the publication's display name — would require discovery module to capture feed/publication titles
- `og-pov-default.png` default path in `format_html()` has no validation; pipeline won't warn if the file is missing in the site repo
- PostHog key should be rotated — it was in a public repo before today's history rewrite

---

## 2026-04-20: Remove session logs from public repo

**Context:** Session logs in `docs/sessions/` were committed to the public repo and needed to be removed without deleting local files.

**What was built:**
- Added `docs/sessions/` to `.gitignore`
- Untracked all existing session files via `git rm -r --cached`
- Rewrote git history with `git filter-repo --path docs/sessions/ --invert-paths --force`
- Re-added `origin` remote (filter-repo removes it automatically) and force pushed

**What broke:** Nothing. All session files remain on disk locally.

**Tech debt:** None introduced.

**Commits:** `7fa2fb9` (gitignore + untrack) → history rewritten → `3068dbc` on remote.

---

## 2026-04-15: Fix Buffer action to read social draft from merged PR body

**Context:** Buffer drafts were showing the original Claude-generated LinkedIn draft, not the version edited and approved in the GitHub PR.

**Root cause:** `buffer-on-merge.yml` was reading `linkedInDraft` from the merged file's YAML frontmatter — the original AI draft. Edits made to the Social Draft block in the PR description were never picked up.

**What was built:**
- Rewrote `buffer-on-merge.yml` to fetch the merged PR body via `gh pr list --search <sha>` (with recency fallback), parse the `### Social Draft` code block, and send that to Buffer. Removed pyyaml dependency.
- Applied the same fix to `buffer-on-merge.example.yml`.
- Added `--diff-filter=A` to the git diff in the "Find merged POV files" step (only newly added files, not modified ones).

**What broke:** Nothing.

**Tech debt:** None introduced.

**Commits:** `b83a66c`

---

## 2026-04-10: --validate pre-flight + zero-context README polish

**Context:** Audited the repo for coherence from a zero-context reader's perspective, then hardened the biggest onboarding traps.

**What was built:**
- **`--validate` pre-flight subcommand** in `pipeline/main.py`. New `validate(config_path) -> list[str]` helper (unit-testable, no sys.exit) + `_run_validate()` CLI wrapper + `--validate` argparse flag that short-circuits before any API calls. Checks: config loads, ANTHROPIC_API_KEY set, voice-guidelines.md exists, SITE_REPO_PATH set and exists, site.content_path exists inside SITE_REPO_PATH, `gh` CLI on PATH and authenticated (via `subprocess.run(["gh", "auth", "status"], timeout=10)`).
- **`tests/test_validate.py`** — 8 new tests covering clean pass + 7 failure modes. Uses a `clean_state` fixture that monkeypatches `drafter.VOICE_GUIDELINES_PATH`, `main_module.shutil.which`, and `main_module.subprocess.run`; individual tests override pieces to simulate each failure.
- **README polish for zero-context readers:**
  - "Who is this for?" block after the pipeline diagram.
  - Explicit Prerequisites section: Python 3.9+, `gh` CLI with install hint, Anthropic API key, site repo with pre-existing content_path.
  - New Step 4 "Pre-flight check" referencing `--validate` before the first real run.
  - "(must already exist)" inline note on `site.content_path` in the config table.
- **Honest data-boundaries section** in README ("What leaves your machine"). Table showing which services are called (Anthropic required, Brave + Firecrawl optional, GitHub for PR), what data each sees, and why. Note that `pipeline/drafter.py` is isolated and can be pointed at an alternate Claude endpoint (e.g. AWS Bedrock) for enterprise data residency. Added because the initial pitch copy was overclaiming "no data leaves your machine" — the user caught it, so the repo docs needed to match the corrected story.
- **Pipeline diagram** updated to show Firecrawl as an optional step between Discovery and Drafting, Brave labeled optional, "first principles" added to the drafting node.

**What broke:**
- First test run failed with `ModuleNotFoundError: No module named 'dotenv'`. The venv was stale — `python-dotenv>=1.0.0` was already in requirements.txt but not installed. `pip install python-dotenv` resolved it. Worth flagging because future contributors with stale venvs will hit the same confusing error.

**Tech debt:**
- `--validate` doesn't check `BRAVE_SEARCH_API_KEY` or `FIRECRAWL_API_KEY` because they're optional. Could surface the existing startup WARNING at pre-flight time. Small improvement.
- README should probably call out the stale-venv trap explicitly.

**Security review:** Ran `/security-review --mode vibe` after commit, before push. No critical findings. Three warnings, all inherited from existing page patterns (cosmetic email gate, shared Apps Script webhook URL, `subprocess.run` on `gh auth status` flagged so future edits don't switch to `shell=True`). Safe to push.

**Commit:** `1a80b54` pushed to `c-b-g-m/pov-pipeline-template` main. 35/35 tests passing.

---

## 2026-04-10: first_principles + audience features + trap fixes

**What was built:**
- Added top-level `audience:` config block (description / knows_already / cares_about) — injects into system prompt so the model calibrates vocabulary and assumed knowledge against a single reader. Originated from beta user feedback on out-of-box usability.
- Added top-level `first_principles:` config block (list of beliefs with optional post_url + post_title) — model reasons *from* them as premises, links to explanatory posts only when a principle is the crux of the argument, max one link per take. Originated from beta user's `feature-first-principles.md` proposal.
- `_build_audience_block()` and `_build_principles_block()` in `drafter.py`, both no-ops when the config key is absent.
- Light validation in `config_loader.py`: both blocks optional, type checks, `post_url` requires `post_title` and must start with `http(s)://`.
- 13 new tests (9 config validation, 4 drafter prompt-building). Full suite: 27 passing.

**Trap fixes bundled in from repo audit:**
- `MAX_CANDIDATES` env var was documented in main.py docstring and piped through the GH Actions workflow but never actually read. Now wired up in `main.py`.
- `voice-guidelines.md` missing was a log.warning + empty-string fallback, producing generic drafts the user would blame on the model. Now CRITICAL exit.
- Theme fallback in `drafter.py` was silent when Claude returned a theme not in config — now logs a WARNING with the invalid theme and the fallback used.
- `brave_queries` with missing `BRAVE_SEARCH_API_KEY` silently returned empty results. Now logs a startup WARNING in `main.py`.
- Malformed `config.yaml` raised a raw Python traceback. Now caught in `config_loader.py` with a clean error message.
- `.gitignore` expanded with explicit warning about committing `config.yaml` with secrets.
- README gained a "Running multiple pipelines" section documenting the "one author, one audience, one site per instance" constraint and how to scale by cloning.
- README's GH Actions section strengthened with rotation guidance for accidentally committed keys.
- CLAUDE.md gained two new "Key Design Decisions" codifying "one author/audience/site per instance" and "fail loud, not silent."

**What broke:** Nothing. All 27 tests pass. `config.example.yaml` validates end-to-end through the real loader.

**Tech debt (flagged during audit, deferred to future PRs):**
- ~~**URL state management**~~ — Fixed 2026-04-22: `mark_processed()` now called only after successful `create_pr()`.
- ~~**Frontmatter YAML injection**~~ — Fixed 2026-04-21: `formatters.py` rewrite switched to `yaml.dump()`.
- ~~**Branch name collision**~~ — Fixed 2026-04-21: collision loop added to `publisher.py`.
- ~~**`firecrawl-py` unconditional install**~~ — Resolved 2026-04-22: inline comment added to `requirements.txt`.

**False positives from audit (verified and rejected):**
- Agent flagged `README.md:46` (`cp env.example .env`) as referencing a nonexistent file. Verified: the file is literally named `env.example` (no dot) and the README matches. Not a bug. Renaming to `.env.example` for convention is cosmetic only.

**Commits & push:**
- Split into two commits via backup-revert-reedit (five files had interleaved feature + trap-fix changes):
  - `cb26eba` — "Add first_principles and audience config blocks" (8 files, +291)
  - `98d7a26` — "Reduce silent failures and onboarding traps" (8 files, +98, -12)
- First push rejected: `origin/main` had commit `e7f8013` ("Remove URL reachability gate that silently dropped candidates (#1)") that wasn't local. Verified it was the user's own work from a prior Claude Code session the night before (2026-04-09 22:33). Touches only `pipeline/discovery.py` — no file overlap, clean rebase. Rebased and pushed to `c-b-g-m/pov-pipeline-template` main.
- Final state: 27/27 tests passing, working tree clean, branch even with origin.

## 2026-04-09: Buffer post-merge sync

**What was built:**
- Synced public template with private repo's Buffer post-merge architecture
- Removed inline Buffer posting from pipeline (was Step 4 in main.py)
- Rewrote `buffer_client.py` from dead v1 REST API to GraphQL
- Created `buffer-on-merge.example.yml` — ready-to-copy post-merge workflow for site repos
- Updated README with full Buffer integration docs, setup steps, and flow diagram
- Updated config.example.yaml, env.example, and pipeline.yml to reflect new flow

**What broke:** Nothing — clean syntax checks, pushed successfully.

**Tech debt:** None introduced.

**Commit:** `b80fd33` pushed to `c-b-g-m/pov-pipeline-template` main.
