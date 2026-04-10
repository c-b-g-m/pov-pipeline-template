# POV Pipeline

An automated content pipeline that discovers industry news, drafts opinionated takes using Claude, and creates GitHub PRs on your website repo for editorial review.

**You provide:** your identity, your industry, your RSS feeds, your editorial voice.
**The pipeline handles:** scanning for articles, drafting takes, and opening PRs for review.

```
RSS Feeds / Brave Search
        |
    Discovery (filter by your keywords + themes)
        |
    Drafting (Claude API + your voice guidelines)
        |
    Publishing (GitHub PR on your site repo)
        |
    You review & merge the PR
        |
    Buffer (post-merge action sends edited social draft)
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
| `audience` | *Optional.* Who you're writing FOR — description, what they already know, what they care about |
| `first_principles` | *Optional.* Foundational beliefs the model reasons FROM, with optional links to explanatory posts |
| `discovery` | RSS feeds, Brave search queries, industry keywords, blocked domains |
| `themes` | Your editorial themes with slugs, labels, and discovery keywords |
| `drafting` | Claude model, output format (mdx/markdown), content section structure |
| `publishing` | Target GitHub repo, base branch, branch prefix |
| `pipeline` | Timezone, rate limits, log file |

### `audience` — who you're writing FOR

Defines the single reader the model calibrates against: vocabulary, assumed knowledge, and framing. Three optional string fields: `description`, `knows_already`, `cares_about`. Leave the block out if you want a generic industry reader.

**This pipeline supports one audience per instance.** See [Running multiple pipelines](#running-multiple-pipelines) below if you need to write for two different readers.

### `first_principles` — foundational beliefs

A list of beliefs you hold as settled. The model reasons *from* them, not just around them. Each entry needs a `belief` string. Optionally attach `post_url` + `post_title` pointing to a post where you've explained the belief in depth — the model will link to it only when the principle is the crux of an argument, never as a passing reference, and at most once per take.

These are YOUR premises, not opinions up for debate. The model will not hedge on them.

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

## GitHub Actions (Automated Scheduling)

The included workflow (`.github/workflows/pipeline.yml`) runs the pipeline daily via GitHub Actions — no local machine dependency.

### Setup

1. In your pipeline repo's GitHub Settings > Secrets, add:
   - `ANTHROPIC_API_KEY` — your Claude API key
   - `TARGET_REPO` — your site repo (e.g., `username/my-website`)
   - `SITE_REPO_TOKEN` — a GitHub PAT with `repo` scope for your site repo
   - (Optional) `BRAVE_SEARCH_API_KEY`, `FIRECRAWL_API_KEY`

2. **Important — config.yaml visibility.** Your `config.yaml` must be readable by GitHub Actions, but it's gitignored by default. You have two options:
   - **Commit it.** Remove `config.yaml` from `.gitignore`. Only do this if your config contains NO secrets (it shouldn't — API keys belong in `.env.local` / GitHub Secrets). Your author name, feeds, themes, and publishing target will become public if your pipeline repo is public.
   - **Generate it at runtime.** Keep `config.yaml` gitignored. Add a workflow step that writes `config.yaml` from a GitHub Actions variable or template before the pipeline runs. This keeps the config private but adds complexity.

   **Never commit `.env*` files or hardcode API keys in `config.yaml`.** If you accidentally commit a key, rotate it immediately — git history is forever.

3. Adjust the cron schedule in `.github/workflows/pipeline.yml` to your preferred time.

### Manual Trigger

The workflow also supports manual dispatch from the GitHub Actions UI with options for:
- **Mode:** full / dry-run / discover-only
- **Max candidates:** override the config default

## Running multiple pipelines

Each instance of this pipeline manages **one author, one audience, one target site.** This is a deliberate design constraint — mixing multiple authors or audiences into a single config produces averaged, edgeless takes that read like nobody in particular wrote them.

If you need to cover multiple audiences (e.g., a technical blog and an executive newsletter), or write under multiple identities (e.g., personal voice and client voice), run multiple copies of this repo:

```bash
git clone https://github.com/YOUR_USERNAME/pov-pipeline-template.git pipeline-technical
git clone https://github.com/YOUR_USERNAME/pov-pipeline-template.git pipeline-exec
```

Each copy gets its own:
- `config.yaml` — separate author, audience, themes, discovery sources, publishing target
- `voice-guidelines.md` — distinct editorial voice
- `.env.local` — can share an `ANTHROPIC_API_KEY`, but `SITE_REPO_PATH` will usually differ
- GitHub Actions schedule — stagger them if you want

They can publish to the same target site repo if you give each a unique `branch_prefix` (`pov-technical/`, `pov-exec/`) and a distinct `content_path`, or they can publish to entirely different site repos. There is no shared state between instances.

## Output Format

The pipeline supports two output formats:

- **MDX** (`output_format: "mdx"`) — for Astro, Next.js, or other MDX-compatible frameworks
- **Markdown** (`output_format: "markdown"`) — for Jekyll, Hugo, or any Markdown-based site

Both formats produce files with YAML frontmatter containing: title, description, sourceUrl, sourceTitle, publishDate, theme, tags, featured, and linkedInDraft.

## Buffer Integration (Post-Merge)

Social posting happens **after you merge a PR**, not during the pipeline run. This ensures only reviewed and edited content reaches LinkedIn (or other platforms).

### Why post-merge?

The pipeline drafts content via Claude, but you'll often edit it before merging. If the pipeline posted to Buffer immediately, the unedited AI draft would go to LinkedIn. The post-merge approach reads the `linkedInDraft` field from the merged file's frontmatter — the version you actually approved.

### Setup

1. Copy `.github/workflows/buffer-on-merge.example.yml` from this repo into your **site repo** at `.github/workflows/buffer-on-merge.yml`
2. Update the `paths` trigger to match your site's content directory
3. In your **site repo's** Settings > Secrets, add:
   - `BUFFER_ACCESS_TOKEN` — your Buffer API token
   - `BUFFER_ORGANIZATION_ID` — your Buffer organization ID (find it in Buffer's URL or API)
4. That's it. When you merge a POV PR, the action reads the social draft from frontmatter and sends it to Buffer as a draft for your approval.

### How it works

```
Pipeline creates PR → You review & edit → Merge to main
                                                |
                              buffer-on-merge.yml triggers
                                                |
                              Reads linkedInDraft from frontmatter
                                                |
                              Sends to Buffer as draft (not auto-published)
                                                |
                              You approve in Buffer UI → Published
```

## Architecture

```
pipeline/
  config_loader.py   — Loads and validates config.yaml
  discovery.py       — Finds candidate articles via RSS + Brave Search
  drafter.py         — Drafts takes via Claude API using your voice guidelines
  formatters.py      — Formats output as MDX or Markdown
  publisher.py       — Creates branches and PRs on your site repo
  buffer_client.py   — Buffer GraphQL client (used by post-merge action)
  main.py            — Orchestrator: runs the pipeline end-to-end
```

## Tests

```bash
pytest tests/ -v
```

Tests cover config validation, discovery filtering logic, and draft response parsing. No API keys required — tests use fixtures.

## License

MIT
