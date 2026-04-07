# POV Pipeline

An automated content pipeline that discovers industry news, drafts opinionated takes using Claude, and creates GitHub PRs on your website repo for editorial review.

**You provide:** your identity, your industry, your RSS feeds, your editorial voice.
**The pipeline handles:** scanning for articles, drafting takes, opening PRs, and optionally queuing social posts.

```
RSS Feeds / Brave Search
        |
    Discovery (filter by your keywords + themes)
        |
    Drafting (Claude API + your voice guidelines)
        |
    Publishing (GitHub PR on your site repo)
        |
    Buffer (optional LinkedIn draft)
```

## Quick Start

### 1. Fork or clone this repo

```bash
git clone https://github.com/YOUR_USERNAME/pov-pipeline-template.git
cd pov-pipeline-template
```

### 2. Set up Python environment

```bash
python3 -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure

Copy the example files and fill in your own values:

```bash
cp config.example.yaml config.yaml
cp voice-guidelines.example.md voice-guidelines.md
cp env.example .env
```

Then edit:
- **`config.yaml`** — your identity, RSS feeds, themes, keywords, publishing target
- **`voice-guidelines.md`** — your editorial voice, tone, structure, and constraints
- **`.env`** — your API keys and site repo path

### 4. Run

```bash
# Discovery only — see what articles are found
python3 -m pipeline.main --discover-only

# Dry run — discover + draft, but don't create PRs
python3 -m pipeline.main --dry-run

# Full run — discover, draft, and create PRs
python3 -m pipeline.main
```

## Configuration

### `config.yaml`

All pipeline behavior is driven by this file. See `config.example.yaml` for a complete working example using a fictional persona.

| Section | What you provide |
|---|---|
| `author` | Your name, role, and specialization |
| `site` | Your domain, content path in your site repo, URL pattern |
| `discovery` | RSS feeds, Brave search queries, industry keywords, blocked domains |
| `themes` | Your editorial themes with slugs, labels, and discovery keywords |
| `drafting` | Claude model, output format (mdx/markdown), content section structure |
| `publishing` | Target GitHub repo, base branch, branch prefix |
| `buffer` | Enable/disable Buffer integration (experimental) |
| `pipeline` | Timezone, rate limits, log file |

### `voice-guidelines.md`

A prose document that defines your editorial voice. Claude reads this before drafting every take. Define:
- Who you are and your perspective
- Your tone (opinionated? measured? provocative?)
- Your target reader
- Content structure (section headings and what goes in each)
- What NOT to do

### Environment Variables

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Claude API key |
| `SITE_REPO_PATH` | Yes (local runs) | Absolute path to your site's git repo |
| `BRAVE_SEARCH_API_KEY` | No | Enables Brave Web Search for broader discovery |
| `FIRECRAWL_API_KEY` | No | Enables full article scraping for better draft quality |
| `BUFFER_ACCESS_TOKEN` | No | Enables Buffer social draft posting (experimental) |

## GitHub Actions (Automated Scheduling)

The included workflow (`.github/workflows/pipeline.yml`) runs the pipeline daily via GitHub Actions — no local machine dependency.

### Setup

1. In your pipeline repo's GitHub Settings > Secrets, add:
   - `ANTHROPIC_API_KEY` — your Claude API key
   - `TARGET_REPO` — your site repo (e.g., `username/my-website`)
   - `SITE_REPO_TOKEN` — a GitHub PAT with `repo` scope for your site repo
   - (Optional) `BRAVE_SEARCH_API_KEY`, `FIRECRAWL_API_KEY`, `BUFFER_ACCESS_TOKEN`

2. **Important:** Your `config.yaml` must be committed to the repo for GitHub Actions to read it. Since it's gitignored by default, you can either:
   - Remove `config.yaml` from `.gitignore` (if your config doesn't contain secrets)
   - Or use a GitHub Actions step to generate it from secrets/variables

3. Adjust the cron schedule in `.github/workflows/pipeline.yml` to your preferred time.

### Manual Trigger

The workflow also supports manual dispatch from the GitHub Actions UI with options for:
- **Mode:** full / dry-run / discover-only
- **Max candidates:** override the config default

## Output Format

The pipeline supports two output formats:

- **MDX** (`output_format: "mdx"`) — for Astro, Next.js, or other MDX-compatible frameworks
- **Markdown** (`output_format: "markdown"`) — for Jekyll, Hugo, or any Markdown-based site

Both formats produce files with YAML frontmatter containing: title, description, sourceUrl, sourceTitle, publishDate, theme, tags, featured, and linkedInDraft.

## Architecture

```
pipeline/
  config_loader.py   — Loads and validates config.yaml
  discovery.py       — Finds candidate articles via RSS + Brave Search
  drafter.py         — Drafts takes via Claude API using your voice guidelines
  formatters.py      — Formats output as MDX or Markdown
  publisher.py       — Creates branches and PRs on your site repo
  buffer_client.py   — Sends social drafts to Buffer (experimental)
  main.py            — Orchestrator: runs the pipeline end-to-end
```

## Tests

```bash
pytest tests/ -v
```

Tests cover config validation, discovery filtering logic, and draft response parsing. No API keys required — tests use fixtures.

## License

MIT
