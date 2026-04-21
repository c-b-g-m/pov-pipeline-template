# Build Log — pov-pipeline-template

## 2026-04-20: GTM Deck — Favicon

**What was built:**
- Added aurora gradient bolt as favicon to `docs/deck/POV Pipeline Deck.html` via inline SVG data URI — no external file needed.

**What broke:** Nothing.

**Tech debt:** None introduced.

---

## 2026-04-20: GTM Deck — Closing Slide

**What was built:**
- Slide 13 (closing) finalized and merged into `docs/deck/POV Pipeline Deck.html`
- Three layout options prototyped as standalone HTML files; Option B (left-panel split) selected
- Final design: circular headshot, aurora gradient on presenter name, Demand AI.Studio wordmark one-line, "Keep going" eyebrow, two CTA cards with URL-level arrows
- `docs/deck/` added to `.gitignore` — personal assets (headshot, URLs) must not reach the public repo
- Three draft option files deleted after merge

**What broke:**
- `background-clip: text` clipped the descender on "George-McFerrin" — fixed with `padding-bottom: 0.12em`
- Chrome `.mark` block persists on every slide — cleared `.mark` content on slide 13's chrome div to suppress the redundant dAIs mark

**Tech debt:** None introduced.

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

## 2026-04-18: GTM community deck brief + Claude Design prompt

**Context:** Chris needed presentation materials for a live GTM community session on the POV Pipeline — audience is go-to-market leaders, not developers.

**What was built:**
- `docs/sessions/pov-pipeline-gtm-deck-brief.md` — 12-slide content brief with headlines, bullets, and speaker notes. Covers: what the workflow does, tools it uses, how to set it up.
- `docs/sessions/pov-pipeline-claude-design-prompt.md` — self-contained Claude Design prompt Chris can paste to generate the visual deck.

**Style reference used:** `dais-pipeline/teaching-ai-fluency/` (outcome contract format, facilitator session structure).

**What broke:** Nothing. No code changes this session.

**Tech debt:** None introduced.

---

## 2026-04-15: Fix Buffer action to read social draft from merged PR body

**Context:** Buffer drafts were showing the original Claude-generated LinkedIn draft, not the version edited and approved in the GitHub PR.

**Root cause:** `buffer-on-merge.yml` was reading `linkedInDraft` from the merged file's YAML frontmatter — the original AI draft. Edits made to the Social Draft block in the PR description were never picked up.

**What was built:**
- Rewrote `buffer-on-merge.yml` in `cazimi-marketing-com` to fetch the merged PR body via `gh pr list --search <sha>` (with recency fallback), parse the `### Social Draft` code block, and send that to Buffer. Removed pyyaml dependency.
- Applied the same fix to `buffer-on-merge.example.yml` in `pov-pipeline-template`.
- Added `--diff-filter=A` to the git diff in the "Find merged POV files" step (only newly added files, not modified ones).

**What broke:** Nothing. Push to `cazimi-marketing-com` main was blocked by branch protection — required a PR (`c-b-g-m/cazimi-marketing-com#33`), merged same session.

**Tech debt:** None introduced.

**Commits:**
- `cazimi-marketing-com`: `7946c01` (merged via PR #33 → `9b7b2f9`)
- `pov-pipeline-template`: `b83a66c`

---

## 2026-04-10: --validate pre-flight + zero-context README polish (Kissinger pitch session)

**Context:** Session was about pitching this repo as a freebie to a fractional-CMO prospect (Kissinger Group). Before pitching, audited the repo for coherence from a zero-context reader's perspective, then hardened the biggest onboarding traps.

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
- **URL state management** (`pipeline/discovery.py`): partial-success GitHub Actions runs mark URLs processed even if PR creation failed, so articles get lost or duplicated unpredictably. Should mark URLs processed only after successful publish, not after drafting. Architectural, not a doc fix.
- **Frontmatter YAML injection** (`pipeline/formatters.py:33-38`): generates frontmatter via string interpolation with ad-hoc escaping. Titles or descriptions containing YAML special chars (colons, backticks, triple quotes) could break downstream parsing. Real latent bug. Fix: use a proper YAML library for frontmatter emission.
- **Branch name collision** (`pipeline/publisher.py:58`): branches are `{prefix}/{date}-{slug}`. Two articles with the same title on the same day would collide and the second `git branch` call would fail. Edge case but real. Fix: append a counter suffix on collision.
- **`firecrawl-py` unconditional install** (`requirements.txt:3`): heavyweight dependency listed even though it's only used when `FIRECRAWL_API_KEY` is set. Fix: move to an optional extras group or add an inline comment.

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
