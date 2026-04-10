# Build Log — pov-pipeline-template

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
