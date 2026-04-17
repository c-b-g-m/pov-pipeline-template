# SOUL.md — POV Pipeline Template

## What This Project Is

An industry-agnostic, open-source content pipeline that discovers articles (RSS + Brave Search), drafts opinionated takes via Claude API, and creates GitHub PRs for editorial review. Config-driven: `config.yaml` + `voice-guidelines.md` define all behavior — no hardcoded industry content. Human reviews every draft before it goes live. Python 3 pipeline. Also forked into demand-ai-studio's freebies.

## Agent Role

Claude maintains and extends the pipeline code. Claude reads `voice-guidelines.md` before any drafting work — it is CRITICAL and missing it exits with an error. Claude validates `config.yaml` structure before running. Claude does NOT hardcode industry content — everything must flow through config.

## What "Done" Looks Like

A task is done when: `python3 -m pipeline.main --validate` passes, a dry run produces correct output format, and GitHub PRs are created for review (not auto-published).

## Key Constraints

- Never hardcode industry, author, or audience content — config-driven only
- `voice-guidelines.md` is required — fail loudly if missing, never silently degrade
- One author, one audience, one site per instance — multi-persona requires multiple clones
- GitHub PRs are the editorial gate — never auto-publish without human review
- `config.yaml` and `voice-guidelines.md` are gitignored (user-specific)

## Tone

Template/tool voice: clear, instructive, opinionated. The pipeline itself produces content with a POV — bland takes are worse than no takes.
