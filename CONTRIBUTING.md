# Contributing to POV Pipeline

Contributions are welcome — bug fixes, documentation improvements, and new features that stay true to the project's design principles.

## Before you start

Read `CLAUDE.md` for the key design decisions. The most important ones:
- **Industry-agnostic, config-driven.** No hardcoded industry content ever enters the codebase.
- **Fail loud, not silent.** Silent degradation is unacceptable. Missing config should error, not fall back quietly.
- **One author, one audience, one site per instance.** Multi-persona setups use multiple repo clones.

If you're unsure whether a change fits, open an issue first.

## Setup

```bash
git clone https://github.com/YOUR_USERNAME/pov-pipeline-template.git
cd pov-pipeline-template
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt
```

## Running tests

```bash
pytest tests/ -v
```

All 86 tests must pass before submitting a PR. If you add functionality, add tests for it.

## Submitting a PR

1. Fork the repo and create a branch from `main`.
2. Make your changes. Keep commits focused — one logical change per commit.
3. Run the full test suite (`pytest tests/ -v`).
4. Open a PR against `main` with a clear description of what changed and why.

## What we're not looking for

- Multi-audience or multi-persona support in a single config (use multiple clones)
- New required dependencies without strong justification
- Changes that introduce silent failure modes
