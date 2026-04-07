# CLAUDE.md

## Project Overview

POV Pipeline — an industry-agnostic, open-source content pipeline that discovers articles, drafts opinionated takes via Claude API, and creates GitHub PRs for editorial review.

## Commands

```bash
python3 -m pipeline.main                 # Full run
python3 -m pipeline.main --dry-run       # Discover + draft, no PRs
python3 -m pipeline.main --discover-only # Discovery only
pytest tests/ -v                         # Run tests
```

## Architecture

- `config.yaml` — user-provided config (gitignored). All identity, industry, feeds, themes, and voice are defined here.
- `voice-guidelines.md` — user-provided editorial voice document (gitignored). Claude reads this before every draft.
- `pipeline/config_loader.py` — loads and validates config.yaml
- `pipeline/discovery.py` — RSS + Brave Search article discovery
- `pipeline/drafter.py` — Claude API drafting with dynamic system prompt from config
- `pipeline/formatters.py` — MDX and Markdown output formatters
- `pipeline/publisher.py` — Git branch + PR creation via `gh` CLI
- `pipeline/buffer_client.py` — Buffer social posting (experimental)
- `pipeline/main.py` — orchestrator

## Key Design Decisions

- **Industry-agnostic:** Zero hardcoded industry content. Everything comes from user config.
- **Config-driven:** Single `config.yaml` + `voice-guidelines.md` define all behavior.
- **GitHub PRs as editorial gate:** Human reviews every draft before it goes live.
- **Output format pluggable:** MDX or Markdown via config flag.
