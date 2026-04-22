# Knowledge Base — pov-pipeline-template

### `git filter-repo` removes origin remote automatically
**Date:** 2026-04-20
**Type:** gotcha
**Context:** Removing committed session logs from public repo history using `git filter-repo`.
**Detail:** `git filter-repo` intentionally removes the `origin` remote as a safety measure after rewriting history. Must re-add it manually (`git remote add origin <url>`) before force pushing.

---

### Sequence for scrubbing committed files from public repo history
**Date:** 2026-04-20
**Type:** pattern
**Context:** Session logs were committed to the public repo and needed to be removed from history without deleting local files.
**Detail:** Correct sequence: add path to `.gitignore` → `git rm -r --cached <path>` → commit → `git filter-repo --path <path> --invert-paths --force` → re-add origin → `git push --force origin main`. Files stay on disk throughout.

---

### GitHub retains loose objects ~90 days after force push
**Date:** 2026-04-20
**Type:** gotcha
**Context:** After scrubbing session logs from repo history.
**Detail:** GitHub doesn't immediately purge orphaned objects after a force push — they persist up to 90 days. For sensitive data requiring immediate removal, contact GitHub Support to request a cache purge.

---

### Buffer action reads from merged PR body, not file frontmatter
**Date:** 2026-04-15
**Type:** decision / gotcha
**Context:** Buffer was sending the original Claude-generated LinkedIn draft instead of the edited version approved in the PR.
**Detail:** The `buffer-on-merge.yml` action was reading `linkedInDraft` from the merged file's YAML frontmatter — the original Claude draft, never touched by PR edits. Users edit the Social Draft block in the PR description; that's the source of truth. Fixed by adding a "Get merged PR body" step (`gh pr list --search <sha>`) and parsing the `### Social Draft` code block from the PR body via regex. File frontmatter is no longer read; pyyaml dependency removed.

## 2026-04-09: Buffer flow is post-merge, not inline
- **Decision:** Buffer posting was removed from the pipeline and moved to a post-merge GitHub Action on the site repo.
- **Why:** The pipeline sends the original AI draft to Buffer before the user reviews/edits it. Moving to post-merge ensures only the reviewed version reaches social.
- **How it works:** The pipeline stores the social draft in `linkedInDraft` frontmatter. A separate GitHub Action (`buffer-on-merge.yml`) in the site repo triggers on push to main, reads the frontmatter from merged files, and sends to Buffer via GraphQL.
- **The example workflow lives at:** `.github/workflows/buffer-on-merge.example.yml` — users copy it into their site repo.

## 2026-04-09: Buffer API is GraphQL, not v1 REST
- **Decision:** Buffer client upgraded from v1 REST API (`bufferapp.com/1/`) to GraphQL (`api.buffer.com`).
- **Why:** Buffer deprecated the v1 API — it returns 401 errors. The GraphQL API is the current supported interface.
- **Key differences:** Auth via `Authorization: Bearer` header (not query param), channel-based targeting (not profile-based), `User-Agent` header required (Cloudflare blocks without it), `saveToDraft: true` to land as drafts.
- **Generalization:** The template uses `organization_id` as a parameter (env var `BUFFER_ORGANIZATION_ID`) instead of hardcoding it.

### Cross-reference positioning claims against actual code paths before writing customer copy
**Date:** 2026-04-10
**Type:** gotcha
**Context:** Wrote a pitch template and landing page with the claim "no data leaves your machine." User caught it — the repo actually calls Anthropic (required), Brave (optional), and Firecrawl (optional).
**Detail:** When writing customer-facing marketing copy for a code project, always grep the actual code paths (`discovery.py`, `drafter.py`, `buffer_client.py`) for outbound API calls before making data-residency or privacy claims. The "no data leaves your machine" framing was lazy and wrong. The honest framing — "no SaaS middle layer; your config, voice doc, and drafts live in your own repo, but the pipeline does call Anthropic/Brave/Firecrawl to do its job" — is sharper and actually holds up in a Fortune 500 security conversation.

### Enumerate service-level data boundaries in a table for enterprise prospects
**Date:** 2026-04-10
**Type:** pattern
**Context:** Fixing the overclaim above, needed a reusable way to describe data flow.
**Detail:** For any pitch or README serving prospects with security review requirements, use an explicit table: service / required? / data sent / why. Each row names exactly what leaves the machine and for what purpose. The "drafter is isolated to one file, can be pointed at Bedrock" callout is a good escape hatch for prospects who need stricter guarantees — it signals the architecture accommodates their constraint without requiring a custom fork.

### Pre-flight validation belongs in its own subcommand, not inline
**Date:** 2026-04-10
**Type:** pattern
**Context:** Adding `--validate` to `pipeline/main.py` to catch onboarding traps before the first real run.
**Detail:** Split the logic into a pure helper (`validate(config_path) -> list[str]`) that returns errors without exiting, plus a thin CLI wrapper (`_run_validate()`) that prints and exits. Makes the helper unit-testable and composable. Tests use `monkeypatch` to stub `shutil.which`, `subprocess.run`, and module-level path constants — simulates every failure mode without touching the real environment.

### `npm run generate-og` regenerates ALL OG images, not just new ones
**Date:** 2026-04-10
**Type:** gotcha
**Context:** Ran `npm run generate-og` to create the new POV Pipeline card in a production site repo.
**Detail:** The Puppeteer script auto-discovers every `index.html` file and regenerates every OG image. Even when visual output is identical, Puppeteer produces ~260 bytes of pixel-level noise per file. When adding a new freebie, expect ~9 other OG files to show up dirty — stage only the new one (`git add og-images/og-new-slug.png`) and `git checkout --` the rest.

### Trust the model over constraining it for AI-savvy forking audiences
**Date:** 2026-04-10
**Type:** decision
**Context:** Evaluating whether to add a `max_principle_links_per_take` config knob for first_principles.
**Detail:** For this template's audience (AI-savvy users who fork and customize), we trust the model with prompt-level instructions rather than adding config knobs to constrain behavior. Forking to tighten is preferred over constraining out of the box. The PR-review gate catches misfires before they ship.

### Top-level config keys for new first-class concepts, not nested
**Date:** 2026-04-10
**Type:** decision
**Context:** Deciding whether `first_principles` and `audience` belonged under `author:` or as top-level keys.
**Detail:** Top-level chosen. Keeps `author:` as a clean identity block, signals that principles/audience are first-class pipeline concepts on par with `themes:`, and scales better as users add more entries. The nested-under-author reading ("these are the author's beliefs") isn't wrong — it's just a different bet.

### One author, one audience, one site per pipeline instance
**Date:** 2026-04-10
**Type:** decision
**Context:** Adding `audience:` to the config and deciding whether to support multi-audience.
**Detail:** Deliberate design constraint. Mixing multiple authors or audiences into one config produces averaged, edgeless takes that read like nobody in particular wrote them. Multi-audience setups use multiple clones of the repo, not multiple entries in one config. Documented in three places: config comment, README's "Running multiple pipelines" section, and CLAUDE.md Key Design Decisions.

### Fail loud, not silent — public templates cannot tolerate silent degradation
**Date:** 2026-04-10
**Type:** decision
**Context:** Handling missing `voice-guidelines.md`, unmapped themes, and Brave queries with no API key.
**Detail:** For a public template, silent degradation is the worst failure mode because users blame the model instead of noticing the config gap. Missing voice guidelines now exit CRITICAL instead of falling back to empty string. Theme mismatches and missing Brave API keys now log WARNINGs naming what's wrong. Documented as a Key Design Decision in CLAUDE.md.

### Document repo constraints in three places for three readers
**Date:** 2026-04-10
**Type:** pattern
**Context:** Ensuring the "one audience per pipeline" constraint wouldn't be invisible to future users and agents.
**Detail:** Public-repo constraints need to live in three places: (1) inline config-file comment for users scanning the example, (2) README section for users reading docs, (3) CLAUDE.md Key Design Decision for agents loading project context. No single location covers all three readers, and forgetting any one creates a trap.

### Splitting mixed-state files across commits via backup-revert-reedit
**Date:** 2026-04-10
**Type:** pattern
**Context:** Needed two clean commits (feature vs. trap fixes) when several files had interleaved changes from both categories.
**Detail:** Copy all mixed files to a /tmp backup with full current state, `git checkout HEAD --` to revert, use Edit to re-apply only the first-commit changes, stage and commit. Then copy the backups back to restore the full state, stage remaining changes, commit. Reliable when `git add -p` would require complex hunk splitting across many files.

### Always verify subagent audit claims against actual code
**Date:** 2026-04-10
**Type:** gotcha
**Context:** Processing an 18-item trap audit from an Explore subagent.
**Detail:** The agent flagged `cp env.example .env` in README as a typo because "the file should be `.env.example`." Verified by reading the actual file and README — the file is literally named `env.example` (no dot) and the README matches. Not a bug. Always verify code-level claims from subagents by reading the files directly before acting; they can hallucinate high-confidence false positives.

### Always fetch and inspect remote state before pushing
**Date:** 2026-04-10
**Type:** gotcha
**Context:** Push rejected because `origin/main` had a commit (`e7f8013`) that wasn't in the local branch.
**Detail:** The unknown commit turned out to be from a different Claude Code session the user ran the night before. Author + timestamp matched, no file overlap with local commits, clean rebase. Always investigate unfamiliar remote state before force-pushing or discarding — it may represent the user's in-progress work from another session. In this repo especially, multi-session work is normal.

### Frame POV Pipeline as "opinion engine, not content generator" for GTM audiences
**Date:** 2026-04-18
**Type:** decision
**Context:** Choosing positioning language for a non-technical GTM leader audience in a community presentation.
**Detail:** "Opinion engine" lands better than "content generator" with GTM leaders because they've already seen generic AI content. The distinction emphasizes that the pipeline reads your voice guidelines and produces opinionated takes — not templates. Pair it with the editorial gate argument: "nothing publishes without your sign-off."

---

### Credentials in git history require rotation, not just code removal
**Date:** 2026-04-21
**Type:** gotcha
**Context:** Removing a hardcoded PostHog key from `formatters.py` that had been in the public template repo since the HTML formatter was written.
**Detail:** Removing a key from code and pushing a new commit doesn't scrub it from git history — every prior commit still exposes it. Required `git filter-repo --replace-text` to rewrite all 19 commits, then a force-push. Also requires rotating the key itself since public repo history should be assumed seen.

---

### `git filter-repo` "already_ran" file blocks re-runs — delete it
**Date:** 2026-04-21
**Type:** gotcha
**Context:** Running `git filter-repo` a second time on this repo (session logs scrubbed 2026-04-20; PostHog key scrubbed 2026-04-21).
**Detail:** If filter-repo was previously run, `.git/filter-repo/already_ran` blocks subsequent runs with an interactive prompt that fails in non-TTY environments. Delete the file (`rm .git/filter-repo/already_ran`) before re-running. Safe to delete — it's just a guard file.

---

### Use yaml.dump() for YAML frontmatter, never string interpolation
**Date:** 2026-04-21
**Type:** pattern
**Context:** Fixing the `_build_content()` formatter in `formatters.py` which manually escaped titles and descriptions with `replace('"', '\\"')`.
**Detail:** Manual string escaping only handles double quotes — titles or descriptions with colons, backticks, or `#` silently produce malformed YAML that downstream MDX processors may reject or misparse. `yaml.dump(fm_dict, default_flow_style=False, allow_unicode=True, sort_keys=False)` handles all edge cases correctly. PyYAML is already a dependency.

---

### JSON-LD `keywords` must be an array, not a comma-delimited string
**Date:** 2026-04-21
**Type:** gotcha
**Context:** Fixing the Schema.org structured data block in `format_html()`.
**Detail:** Schema.org's `keywords` field expects an array. Using `", ".join(tags)` produces a string that structured data parsers iterate character-by-character. Fix: pass the `tags` list directly to `json.dumps()`.

---

### HTML formatter in a public template must be 100% config-driven — no hardcoded identity
**Date:** 2026-04-21
**Type:** decision
**Context:** The `format_html()` function was built for an early implementation and never generalized before open-sourcing.
**Detail:** Every identity string — site name, author name, OG tags, nav logo, footer, CTA copy and URL, analytics keys — must come from config or be absent. Any hardcoded value makes the formatter unusable for any other user. The CTA section pattern (omit `site.cta` from config entirely to suppress the HTML block) is the right model for optional sections.

---

### Heading consistency between publisher and Buffer workflow regex is load-bearing
**Date:** 2026-04-22
**Type:** gotcha
**Context:** Auditing the Buffer integration during fork-readiness review.
**Detail:** `publisher.py` wrote `### LinkedIn Draft`; the workflow regex looked for `### Social Draft`. Buffer silently skipped every post with no error. Any heading in a PR body template that's matched by a downstream regex is a coupled contract — treat it that way.

---

### Tracked ops docs expose internal names on public repos
**Date:** 2026-04-22
**Type:** gotcha
**Context:** Fork-readiness audit found client and internal project names in build-log.md and knowledge-base.md.
**Detail:** Both files were git-tracked and contained internal project names and client domains. For a public repo, ops docs need to be scrubbed or gitignored before going wide. `docs/sessions/` was correctly gitignored; the broader docs/ directory was not.

---

### Dead config fields in example configs create false user expectations
**Date:** 2026-04-22
**Type:** pattern
**Context:** Removing `url_pattern` and `target_repo` from config.example.yaml.
**Detail:** Config fields that exist in the example but are never read by code cause real confusion. Either implement the field or remove it. A field with a real-looking value and no effect is a trap for new users.

---

### Use a queue class to mock sequential subprocess calls in publisher tests
**Date:** 2026-04-22
**Type:** pattern
**Context:** Writing tests for publisher.py, which makes multiple sequential git calls.
**Detail:** A `_RunQueue` class that pops `(returncode, stdout, stderr)` tuples in order — defaulting to `(0, "", "")` for extras — is cleaner than a dict keyed on command prefix. Git makes multiple calls with the same subcommand (e.g., two `git checkout` calls), so command-keyed dicts break down.

---

### Action-first one-liner above the fold for README onboarding
**Date:** 2026-04-22
**Type:** pattern
**Context:** Evaluating whether the public repo's README gave cold visitors an obvious entry point.
**Detail:** Put a single "New here? → do X" line immediately after the tagline, before any diagrams or context sections. Cold visitors scan for action before they read. A one-liner that links directly to the Quick Start anchor catches them before the architecture diagram does.

---

### Minimum-required table in Quick Start config steps
**Date:** 2026-04-22
**Type:** pattern
**Context:** Step 3 of Quick Start said "fill in your own values" with no guidance on what was blocking vs. optional.
**Detail:** When a setup step involves a multi-field config file, add a small table listing the minimum fields required to proceed. Label everything else optional. "Fill in your own values" produces analysis paralysis; a five-row table with required fields named explicitly does not.

---

### Repeat blockers at the point of use, not just in prerequisites
**Date:** 2026-04-22
**Type:** pattern
**Context:** `site.content_path` must-exist requirement was in Prerequisites but not in Step 3 where users actually encounter it.
**Detail:** A prerequisite mentioned once at the top is often forgotten by the time the user hits the relevant step. For any hard blocker (directory must exist, token must have scope X), repeat it as a callout at the exact step where it will bite them — not just in the prerequisites list.

---

### Patch _graphql directly for buffer_client tests, not urlopen
**Date:** 2026-04-22
**Type:** pattern
**Context:** Writing tests for buffer_client.py, which makes HTTP calls via urllib.
**Detail:** All HTTP in buffer_client flows through `_graphql`. Patching `pipeline.buffer_client._graphql` directly avoids dealing with request/response byte encoding and keeps tests readable. Don't go lower.

---

### Stale tech debt in build log sent us down a resolved path
**Date:** 2026-04-22
**Type:** gotcha
**Context:** Reviewing the open tech debt list before starting work on YAML injection, branch collision, and firecrawl.
**Detail:** All three items were already fixed in April 21–22 sessions but the April 10 build log entry was never updated. Strike through tech debt entries in the original build log entry at the time of fix, not just in the session that introduced them.

---

### Paired tuples over parallel lists for draft-to-URL tracking in the orchestrator
**Date:** 2026-04-22
**Type:** pattern
**Context:** Fixing URL state management — `processed_urls` was a separate list populated at draft time, decoupled from PR outcomes.
**Detail:** Replaced `drafts = []` + `processed_urls = []` with `drafts_with_urls = [(draft, source_url), ...]`. Keeps each draft bound to its source URL through the PR loop so `mark_processed()` can be called only on successes. Parallel lists diverge silently; paired tuples make the relationship explicit and harder to break.

---

### Testing `main()` requires `tmp_path` for SITE_REPO_PATH
**Date:** 2026-04-22
**Type:** gotcha
**Context:** Writing `tests/test_main.py` — first attempt used a fake string path and failed on the `os.path.isdir()` guard.
**Detail:** `main()` validates that `SITE_REPO_PATH` is a real directory before reaching the code under test. Passing a non-existent fake path causes `sys.exit(1)` before the test logic runs. Fix: use pytest's `tmp_path` fixture and `monkeypatch.setenv("SITE_REPO_PATH", str(tmp_path))` — creates a real directory with no side effects.
