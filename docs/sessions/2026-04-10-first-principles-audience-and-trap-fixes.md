# Session: first_principles + audience feature, plus repo audit and trap fixes

**Date:** 2026-04-10
**Branch:** main
**Final commits pushed:** `cb26eba`, `98d7a26`

---

## User

I'm excited to share that this public repo has been reviewed by a beta user. This are the thoughts shared. Please review and let's chat. /Users/christengeorge-mcferrin/Downloads/feature-first-principles.md

## Assistant

[Read the proposal file — a detailed feature request from a beta user to add a `first_principles` field to `config.yaml` that lets users define axiomatic beliefs Claude should never contradict and can reason from. Each principle could carry an optional link to an explanatory post. Proposed schema under `author:`, proposed prompt injection in `drafter.py: _build_system_prompt`, proposed validation rules, and an explanation of why system-prompt placement matters.]

I read the proposal. Quick take:

**This is a strong suggestion and fits the template's design cleanly.** It's pure config + one prompt-injection block — no new files, no architectural churn, stays industry-agnostic. It complements `voice-guidelines.md` without overlapping it (tone/structure vs. axiomatic beliefs).

**What I like:**
- The system-prompt-vs-user-message reasoning on line 66 is correct — it matters and the beta user clearly understands prompt hierarchy.
- The "link only when the principle is the crux" guard is the right call. Without it, every take turns into a self-link farm.
- Optional `post_url`/`post_title` means early users can adopt it before they've written the explanatory posts.

**Two things worth discussing before we build:**

1. **Link restraint is doing a lot of work in the prompt.** "Only when genuinely central" is subjective. In practice Claude may either over-link or never link. Worth deciding: do we trust the model, or add a config knob like `max_principle_links_per_take: 1` (already implied) and a stricter phrasing? I'd start with the proposal as-written and tune after we see real drafts.

2. **Validation scope.** The proposal says validate `belief` is a string and `post_url` requires `post_title`. I'd also check `post_url` starts with `http` — cheap guard against typos becoming broken links in published posts.

**Not blockers, just flags.** The implementation sketch matches the actual `_build_system_prompt` signature in `pipeline/drafter.py:63`, so it'll drop in without refactoring.

Want me to (a) implement it as-specified, (b) implement with the URL validation tweak, or (c) keep discussing before building?

---

## User

Let's keep discussing. For this specific repo, I think we can assume a certain level of AI savvy. So with that I would also infer some trust for the model. I think it would be better to allow them to fork and customize than constrain out of the box. It also seems like the validation/feedback loop would help reduce issues with this.

## Assistant

Agreed on both counts. Trust the model out of the box, let forkers tighten if they want, and lean on the existing PR-review gate to catch misfires before anything ships. That posture also keeps the template's "config + voice doc, nothing clever" feel intact.

One follow-up worth deciding now, since it shapes the implementation:

**Should `first_principles` live under `author:` (as the proposal has it) or as a top-level key?**

The proposal nests it under `author:` alongside `name`/`role`/`specialization`. That reads naturally — these are *the author's* beliefs. But it also means `author:` starts mixing identity (who they are) with editorial substance (what they think), and the block could grow long enough to make `author:` feel cluttered.

A top-level `first_principles:` key would keep `author:` as a clean identity block and signal that principles are a first-class pipeline concept, on par with `themes:` and `voice-guidelines.md`. The tradeoff is one extra line in `_build_system_prompt` to fetch it, and a slightly less obvious "whose beliefs are these?" read in the YAML.

I lean top-level — it scales better as users add 5-10 principles and matches how `themes:` is already structured. But the proposal's nesting isn't wrong, just a different bet. Which way do you want it?

---

## User

Top-level feels better to me. My goal is to make this usable out of the box, which would mean making it clear to the model whose voice and POV they are writing *in* as well as who the ICP is that they're writing *for*. What are your thoughts given this context?

## Assistant

You're right, and it's a real gap in the template today — independent of `first_principles`. Right now the model knows who's writing (`author.name/role/specialization`) but has to *infer* the reader from voice guidelines, which is fragile. A take aimed at a CFO reads very differently from one aimed at a practitioner, even with identical voice and beliefs.

I'd add a sibling top-level `audience:` block alongside `first_principles:`. Three clean concerns, three top-level keys: `author:` (who's writing), `audience:` (who's reading), `first_principles:` (what's settled). All three feed `_build_system_prompt`, and voice-guidelines.md stays focused on tone/structure.

Rough shape — keep it minimal so it doesn't feel like a form to fill out:

```yaml
audience:
  description: "Climate tech operators and early-stage founders"
  knows_already: "Industry basics, common acronyms, the major players"
  cares_about: "What's actually working, where capital is flowing, what to ignore"
```

Three fields, all strings, all optional. The model gets enough to calibrate vocabulary and assumed knowledge without us prescribing a rigid ICP schema.

**Tradeoff to flag:** this expands the beta user's proposal from "one feature" to "two related features shipped together." Coherent, but bigger. Two ways to play it:

1. **Ship together** as one PR — the template gets a meaningful out-of-box upgrade in a single pass, and the system prompt only changes once.
2. **Ship `first_principles` first**, then `audience:` as a follow-up — honors the beta user's specific contribution and lets you validate each change independently.

I lean (1) because the two features reinforce each other and the template is still early enough that bundling won't disrupt anyone. But (2) is the more respectful move toward the beta user. Which matters more to you here?

---

## User

1

## Assistant

Here's the plan. Five files, one PR-sized change.

**1. `config.example.yaml`** — Add two new top-level blocks after `author:`/`site:`, before `discovery:`:

```yaml
audience:
  description: "..."
  knows_already: "..."
  cares_about: "..."

first_principles:
  - belief: "..."
    post_url: "..."      # optional
    post_title: "..."    # optional
  - belief: "..."
```

Include 2-3 realistic examples matching the Jordan Rivera climate-tech persona so new users can see what "good" looks like.

**2. `pipeline/config_loader.py`** — Extend `_validate` with light checks. Both blocks optional (template stays usable without them). For `first_principles`: each entry needs `belief` (string); if `post_url` present, require `post_title` and that URL starts with `http`. For `audience`: no required subfields — if block exists, just verify it's a dict.

**3. `pipeline/drafter.py`** — Extend `_build_system_prompt` to inject both blocks when present. `audience` block goes near the top (shapes who the ghostwriter is writing *for*, sits alongside the author framing). `first_principles` block goes after the voice/structure instructions but before the output format spec — reasoning premises, not formatting rules. Both are no-ops when the config keys are absent.

**4. `README.md`** — Add a short section documenting both fields, with the "link only when central" behavior called out so users know what to expect.

**5. `tests/`** — Check existing test structure first; add coverage for: validation passes with both blocks absent, validation fails on malformed `first_principles`, system prompt includes blocks when present and omits them when absent.

**Two small calls I'm making without asking:**
- `audience` block is flat (three string fields), not a list. One audience per pipeline. If someone needs multi-audience, they fork.
- `first_principles` injection wording stays close to the beta user's proposal — it's good prose, no reason to rewrite it.

**One question before I build:** is this personal or client work? Asking because it determines where the session transcript lands at wrap-up and whether I should scrub the beta user's name/examples from any docs.

Ready to build on your go.

---

## User

Are the instructions clear that they would need to fork to create a new audience pipeline? Remember, this is a public repo so it's important that the steps are clear and simple so that both humans and agents can build this quickly and well.

## Assistant

Honest answer: no, not as I described it. I said "one audience per pipeline, fork if you need more" in *this conversation*, but that guidance wouldn't survive into the repo. A user (or an agent) reading `config.example.yaml` would see a flat `audience:` block and have no idea whether multi-audience is a planned feature, a missing feature, or an intentional constraint.

Three places to make it explicit, each serving a different reader:

**1. Inline comment in `config.example.yaml`** — the fastest path for someone scanning the file:

```yaml
# ─── Audience ───────────────────────────────────────────────────────────────
# Who you're writing FOR. One audience per pipeline — the model calibrates
# vocabulary, assumed knowledge, and framing against this single reader.
#
# Need to write for two different audiences? Run two copies of this repo,
# each with its own config.yaml and voice-guidelines.md. Don't try to
# encode multiple audiences here — the model will average them and the
# takes will lose their edge.
```

**2. A short "Running multiple pipelines" section in `README.md`** — for the user who's already decided they need this and is looking for the how. Covers: clone the repo twice into separate directories, give each its own `config.yaml`, `voice-guidelines.md`, and `.env.local`, point each at a different target site repo (or the same repo with different `branch_prefix`). Half a page, not more.

**3. A line in `CLAUDE.md`** — so any agent working in a fork of this template understands the constraint without having to infer it from config comments. One sentence under "Key Design Decisions": *"One audience per pipeline instance. Multi-audience setups use multiple clones, not multiple config entries."*

The reason to hit all three: humans scanning the example file get the inline warning, humans reading docs get the how-to, and agents loading project context get the architectural rule. No single location covers all three readers.

Same question applies to `first_principles` — should I add parallel "these are *your* beliefs, not a debate club" framing to its config comment? I think yes, but lighter touch since the risk of misuse is lower.

Want me to fold this into the plan and proceed, or keep refining?

---

## User

Yes, please. Go ahead and review the project as a whole -- are there similar such traps that should be cleaned up and clarified at this time?

## Assistant

[Loaded TaskCreate/TaskUpdate/TaskList tools. Created three tasks: audit, implement feature, document trap fixes. Delegated the audit to an Explore subagent with a detailed brief defining what counts as a "trap" and scoping fixes to documentation / config comments / validation messages / README edits rather than architectural refactors. The agent returned an 18-item report across HIGH/MEDIUM/LOW severity. Then verified two code-level claims — env.example filename and MAX_CANDIDATES env var — and filtered the list.]

Audit done. I verified the two code-level claims — one's a real bug, one's a false positive. Filtered list below.

**Real traps worth fixing now:**

**Silent failure class** (the most dangerous category for a public repo — user thinks it's working, it isn't):

1. **`MAX_CANDIDATES` env var is a broken promise.** Documented in `pipeline/main.py:21`, set in `env.example:28`, piped through `.github/workflows/pipeline.yml:59` — but `main.py` never reads it and `discovery.py:223` only uses the config value. Users overriding via GH Actions input get zero effect. **Real bug.** Fix: read env var in `main.py` and pass into discovery.

2. **Voice guidelines missing → empty string → generic drafts, log-level WARNING.** `pipeline/drafter.py:26-32`. A user who forgets to copy the example file gets low-quality takes and may blame the model. Fix: elevate to CRITICAL and exit, unless explicitly opted out.

3. **Theme mismatch silently falls back to first theme.** `pipeline/drafter.py:216-218`. No log line. Fix: log a WARNING when fallback fires.

4. **Brave queries in example config produce zero results without `BRAVE_SEARCH_API_KEY`.** `pipeline/discovery.py` returns `[]` silently. User wonders why discovery is thin. Fix: comment in `config.example.yaml` stating Brave requires an API key + paid plan, and log a WARNING at startup if `brave_queries` exist but the key is missing.

**Setup/onboarding class:**

5. **`config.yaml` gitignored by default, but GitHub Actions needs it committed.** README flags this but doesn't warn about the secret-leak risk or show the safer pattern (generate config from GH Secrets at runtime). For a public repo this is the single biggest "someone will commit their API key" risk. Fix: expand README section, add a stronger warning in `.gitignore` comment.

6. **`site.content_path` must already exist in the target site repo.** `pipeline/publisher.py` fails late (after drafting) with a confusing error. Fix: validate in `main.py` before drafting starts.

7. **`gh` CLI must be installed and authenticated to the target repo.** Failure mode is cryptic stderr. Fix: `gh auth status` + `gh repo view <target>` upfront with clear error messages.

8. **Malformed YAML in `config.yaml` raises a raw Python traceback.** `pipeline/config_loader.py:37-38`. Fix: try/except with a clean error.

**Documentation class:**

9. **"One author, one site, one audience" is nowhere stated.** This is the trap we already discussed. Fixing as part of the main feature work.

**False positive I verified and rejected:**

- The agent flagged `README.md:46` (`cp env.example .env`) as a typo because the file "should be" `.env.example`. I checked: the file is actually named `env.example` and the README matches. Not a bug. Could rename for convention but it's cosmetic — I'd leave it.

**Out of scope for this pass (flagging for later):**

- URL state management (`pipeline/discovery.py`) — partial-success runs lose articles. Architectural, not a doc fix.
- Frontmatter escaping uses string interpolation instead of a YAML library (`pipeline/formatters.py`) — real latent bug, deserves its own PR.
- Branch name collision on duplicate titles same day — edge case.
- `firecrawl-py` always installed even when unused — optimization, not a trap.

---

**My recommendation for this PR's scope:**

**Bundle:** items 1, 2, 3, 4, 5, 8, 9 + the original `first_principles` / `audience` feature.

**Defer:** items 6, 7 (real but need a bit more design — do I want `main.py` reaching into the site repo before drafting? Yes, probably, but it deserves its own think).

**Park in `docs/build-log.md`:** the three "out of scope" items above, so they don't get lost.

This keeps the PR focused on "make silent failures loud" + "document constraints" + "ship the new feature" — one coherent theme: **reducing surprise for a first-time user**.

One more question before I write code: **personal or client work?** I need to know before wrap-up where the transcript lands.

---

## User

This is public work that will be used as a lead magnet for dAIs. So, neither.

## Assistant

[Saved a new user memory category for "dAIs lead magnet" work — a third category beyond personal and client, with higher public-facing quality standards. Also saved a project memory about the beta user feedback source.]

Got it — saved that dAIs context to memory so future sessions know this repo has a higher bar than personal work. Starting the build now.

[Executed the implementation: config_loader validation + YAML try/except, drafter audience and principles block builders and prompt injection, voice-guidelines elevation to CRITICAL, theme fallback warning, main.py MAX_CANDIDATES wiring and Brave warning, config.example.yaml with audience/first_principles/Brave/content_path comments, .gitignore secret warning, README with new doc sections and Running-multiple-pipelines and stronger GH Actions warning, CLAUDE.md design decisions, tests for validation and prompt building (13 new tests). Ran the full suite: 27/27 passing. Verified config.example.yaml passes the full loader end-to-end.]

All green. Here's what shipped:

**Feature: audience + first_principles**
- `config.example.yaml` — two new top-level blocks with detailed comments explaining the "one audience per pipeline" constraint inline
- `pipeline/config_loader.py` — light validation (optional blocks, type checks, URL format check, post_title required with post_url)
- `pipeline/drafter.py` — `_build_audience_block()` and `_build_principles_block()` inject into the system prompt only when configured
- 4 new drafter tests + 9 new config validation tests (all 27 tests pass)

**Trap fixes bundled in:**
- `MAX_CANDIDATES` env var is now actually wired up in `main.py:88-93` (was documented, never read — real bug)
- `voice-guidelines.md` missing now exits with CRITICAL instead of silently producing generic drafts
- Theme fallback in `drafter.py:229-235` now logs a WARNING with the invalid theme and the fallback used
- Brave queries + missing API key now emits a startup WARNING in `main.py:111-117`
- Malformed YAML in `config.yaml` now raises a clean error instead of a Python traceback
- `.gitignore` expanded with an explicit warning about committing config.yaml with secrets
- `README.md` — new "Running multiple pipelines" section, stronger GH Actions config.yaml warning with rotation guidance, doc sections for `audience` and `first_principles`
- `CLAUDE.md` — two new "Key Design Decisions" codifying "one author, one audience, one site" and "fail loud, not silent"

**Parked in the out-of-scope list** (for you to review later, not done now):
- URL state management (`discovery.py`) losing articles on partial-success runs — architectural
- Frontmatter uses string interpolation instead of a YAML lib (`formatters.py`) — real latent bug
- Git branch name collision on same-day duplicate titles — edge case
- `firecrawl-py` unconditionally installed — optimization

Want me to add those four to `docs/build-log.md` so they don't get lost, or leave them in this conversation for you to handle separately?

---

## User

They can get logged.

## Assistant

[Updated docs/build-log.md with a full entry for today's work, including the feature, the trap fixes, the four deferred tech-debt items with file:line references and proposed fixes, and the false positive documented so a future audit doesn't flag it again.]

Logged. The build-log now has a full entry for today's work with the four deferred items called out as named tech debt with file:line references and proposed fixes, plus the false positive documented so a future audit doesn't flag it again.

Anything else before we wrap up, or ready for the session wrap-up protocol?

---

## User

Does anything need to be pushed?

## Assistant

[Checked git status and unpushed commits.]

Nothing is pushed because **nothing is committed yet.** Current state:

- Branch `main` is even with `origin/main` (no unpushed commits)
- 11 modified files sitting uncommitted in the working tree — today's feature + trap fixes + build log

So the sequence would be: **commit → push.** I'll need your explicit go-ahead for both (pushing to GitHub is on your hard-stops list, and I don't commit without being asked either).

One thing worth deciding before committing: **one commit or two?** Options:

1. **Single commit** — "Add audience + first_principles features; fix silent-failure traps from repo audit." Simple, one PR-sized unit of history.
2. **Two commits** — (a) the feature (audience + first_principles + tests + docs for those), (b) the trap fixes (MAX_CANDIDATES, voice-guidelines elevation, theme warning, Brave warning, YAML error handling, gitignore, CLAUDE.md). Cleaner history, each commit revertable independently.

I lean (2) because the trap fixes are a distinct "reduce surprise" theme from the new-feature work, and if one of the trap fixes turns out to cause a problem you can revert it without losing the feature. Takes one extra commit's worth of effort.

Also worth noting: these commits will go **directly to `main`**, not a branch + PR. Is that what you want for a public template, or should I create a branch and open a PR against your own repo so the changes get a review gate? A PR would let you see the full diff on GitHub before merging, which feels right for a public lead-magnet repo where clean history matters.

**Your call on three things:**
1. One commit or two?
2. Straight to main or branch + PR?
3. Push after committing, or commit now and push later?

---

## User

Two and in this instance it's okay to push directly to main as I'm the reviewer.

## Assistant

[Backed up the five mixed-state files to /tmp, reverted them to HEAD, applied only the feature-related edits to each, staged and committed commit 1 (feature). Then restored the backups to bring back the trap-fix state, staged and committed commit 2 (trap fixes).]

[Commit 1: `7fc7e8f` "Add first_principles and audience config blocks" — 8 files, 291 insertions.]
[Commit 2: `2851aee` "Reduce silent failures and onboarding traps" — 8 files, 98 insertions, 12 deletions.]

[Attempted push, rejected with "fetch first" — remote had a commit I didn't have locally.]

Push rejected — remote has commits I don't have locally. Let me investigate before doing anything destructive.

[Fetched origin. Found one unknown commit: `e7f8013` "Remove URL reachability gate that silently dropped candidates (#1)", authored by c-b-g-m, touching only pipeline/discovery.py.]

Found it. There's one commit on `origin/main` that I don't have locally:

```
e7f8013 Remove URL reachability gate that silently dropped candidates (#1)
```

Authored by you (`c-b-g-m <christen@cgm-marketing.com>`) on 2026-04-09 22:33. It only modifies `pipeline/discovery.py` (removes 21 lines, adds 2). The PR number `#1` suggests it came from a merged pull request, possibly one you merged from GitHub's UI earlier.

**Good news:** no file overlap with my two commits, so a rebase will be clean — no conflicts. My commits will just sit on top of it.

**Two questions before I proceed:**

1. **Do you recognize this commit?** If yes, great, I'll rebase and push. If no, we should stop and inspect it before anything else — an unexpected commit on a public repo's main is worth understanding.

2. **Assuming you recognize it: rebase or merge?** Rebase keeps history linear, which matches the clean style of your existing commit log. Merge would introduce a merge commit. I'd go rebase.

I'm going to wait for your call on #1 before touching anything — an unknown remote commit is exactly the kind of "unfamiliar state" your instructions tell me to investigate rather than steamroll.

---

## User

Does it say who it was? I was working on this in a different session in Code last night so it could be me.

## Assistant

Yes — it's you.

- **Author:** `c-b-g-m <christen@cgm-marketing.com>`
- **Timestamp:** 2026-04-09 22:33:50 -0500 (last night)
- **Matches** the `Git user: c-b-g-m` from this repo's config

That lines up exactly with a different Claude Code session you had last night. Safe to proceed.

Going to rebase my two commits on top of it and push. Confirming you want me to do that — just reply go and I'll run `git rebase origin/main && git push origin main`.

---

## User

Yes, please.

## Assistant

[Rebased cleanly with no conflicts. New commit SHAs: cb26eba, 98d7a26. Ran the test suite — 27/27 still green. Pushed to origin/main successfully.]

Pushed. Both commits are now live on `c-b-g-m/pov-pipeline-template` main:

- `cb26eba` Add first_principles and audience config blocks
- `98d7a26` Reduce silent failures and onboarding traps

[Attempted to clean up /tmp backup directories — blocked by hard-denied `rm -rf` in global settings, correctly.]

**Done. Shipped to main:**

- `cb26eba` — first_principles + audience feature
- `98d7a26` — trap fixes (silent-failure hardening)

Both committed, rebased onto your overnight `#1` PR, tests green at 27/27, pushed to `c-b-g-m/pov-pipeline-template`. Branch is clean and even with origin.

Ready for wrap-up whenever you are.

---

## User

Thank you. Please wrap up.

## Assistant

[Running the four-step wrap-up protocol: session export, knowledge capture, build log update, session summary.]
