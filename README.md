# POV Pipeline

An automated content pipeline that discovers industry news, drafts opinionated takes using Claude, and creates GitHub PRs on your website repo for editorial review.

**You provide:** your identity, your industry, your RSS feeds, your editorial voice.
**The pipeline handles:** scanning for articles, drafting takes, and opening PRs for review.

**New here?** Fork this repo → follow [Quick Start](#quick-start) → run `--validate` before anything else.

```
RSS Feeds + Brave Search (optional)
        |
    Discovery (filter by your keywords + themes)
        |
    Firecrawl (optional — scrape full article text)
        |
    Drafting (Claude API + your voice guidelines + first principles)
        |
    Publishing (GitHub PR on your site repo)
        |
    You review & merge the PR
        |
    Buffer (post-merge action sends edited social draft)
```

## Who is this for?

Fractional CMOs, consultants, founders, thought leaders, and product marketers who want to publish opinionated takes on industry news consistently — without becoming a full-time content operation. If you already have strong views but not enough hours to write every week, this pipeline drafts takes in your voice and hands you editable PRs. You review, edit, and merge. The pipeline does the drafting; you stay in control of the final word.

You do **not** need to be a developer to run it, but you will touch a terminal and a GitHub repo. If that's a hard stop, this isn't the right tool yet.

## Quick Start

### Prerequisites

Before you start, confirm you have:

- **Python 3.9+** — check with `python3 --version`
- **`gh` CLI** — GitHub's command-line tool, installed and authenticated. Install with `brew install gh` (macOS) or see https://cli.github.com, then run `gh auth login`.
- **An Anthropic API key** — get one at https://console.anthropic.com
- **A site repo** — an existing GitHub repo where drafts will be opened as PRs. The target directory inside that repo (e.g. `content/posts/`) must already exist.

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

> Contributing or running tests? Use `pip install -r requirements-dev.txt` instead — it includes pytest.

### 3. Configure

Copy the example files and fill in your own values:

```bash
cp config.example.yaml config.yaml
cp voice-guidelines.example.md voice-guidelines.md
cp env.example .env.local
```

Then edit:
- **`config.yaml`** — your identity, RSS feeds, themes, keywords, publishing target
- **`voice-guidelines.md`** — your editorial voice, tone, structure, and constraints
- **`.env.local`** — your API keys and site repo path

**Minimum required to get through `--validate`:**

| What | Where |
|---|---|
| `author.name`, `author.role`, `author.specialization` | `config.yaml` |
| `site.domain`, `site.content_path` | `config.yaml` |
| At least one RSS feed under `discovery.rss_feeds` | `config.yaml` |
| `ANTHROPIC_API_KEY` | `.env.local` |
| `SITE_REPO_PATH` | `.env.local` |

Everything else (`audience`, `first_principles`, `themes`, `brave_queries`, Buffer) is optional — add it once the pipeline is running.

> **Important:** The directory you set as `site.content_path` (e.g. `src/content/pov`) must already exist in your site repo before you run the pipeline. Create it and commit it if it doesn't.

### 4. Pre-flight check

Before your first real run, verify your config, env vars, and prerequisites:

```bash
python3 -m pipeline.main --validate
```

This checks that `config.yaml` loads, `ANTHROPIC_API_KEY` is set, `voice-guidelines.md` exists, `SITE_REPO_PATH` points at a real directory containing your `site.content_path`, and the `gh` CLI is authenticated. No API calls are made. Fix any reported issues before moving on.

A passing run prints `[OK]` for each check. Any `[FAIL]` line includes a message telling you what to fix.

### 5. Run

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
| `site` | Your domain, content path in your site repo (must already exist), optional OG image path |
| `audience` | *Optional.* Who you're writing FOR — description, what they already know, what they care about |
| `first_principles` | *Optional.* Foundational beliefs the model reasons FROM, with optional links to explanatory posts |
| `discovery` | RSS feeds, Brave search queries, industry keywords, blocked domains |
| `themes` | Your editorial themes with slugs, labels, and discovery keywords |
| `drafting` | Claude model, output format (mdx/markdown), content section structure |
| `publishing` | Target GitHub repo, base branch, branch prefix |
| `pipeline` | Timezone, rate limits, log file |

### `site.og_image` — OG image for HTML output

If you use `output_format: html`, each article gets an OG `<meta>` tag pointing to this path. The default is `/og-images/og-pov-default.png` — a path relative to your site root. **You must supply this file in your site repo.** The pipeline won't warn you if it's missing; broken OG images are silent. Either set `og_image` in your config to a path that exists, or leave the field out and create the default file in your site repo.

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

## What leaves your machine

This is an important question for anyone running the pipeline inside a regulated or privacy-sensitive environment. There is **no SaaS middle layer** — your `config.yaml`, `voice-guidelines.md`, discovered candidates, and drafts all live in your own repo and on your own disk. But the pipeline does call three external APIs to do its job. Here is exactly what each one sees:

| Service | Required? | Data sent | Why |
|---|---|---|---|
| **Anthropic (Claude)** | Yes | The article text or summary, your `voice-guidelines.md`, your `audience` and `first_principles` config blocks, and the drafting prompt | This is what writes the take. Without it, the pipeline cannot draft. |
| **Brave Search API** | No | The search query strings you define in `config.yaml` under `discovery.brave_queries` | Broader article discovery beyond your RSS feeds. Skip it to stay RSS-only. |
| **Firecrawl** | No | The URL of each candidate article | Fetches full article text so Claude has more to work with than the RSS summary. Skip it and Claude drafts from the summary only. |
| **GitHub** | Yes | Your drafted content, as a pull request on the site repo you configured | This is the editorial gate — every draft goes through a PR on your own repo. |
| **RSS feeds** | — | Nothing outbound beyond a standard HTTP GET | Public feeds. No credentials, no identifiers. |

Your config, voice doc, first principles, and drafts never touch any third-party storage service. The only content sent to Anthropic is what's needed to write a single draft; nothing is retained or used by the pipeline after the response comes back. If you need to run this with stricter guarantees (e.g. an enterprise AWS Bedrock deployment of Claude instead of the public Anthropic API), the drafter is isolated to `pipeline/drafter.py` and can be pointed at an alternate Claude endpoint with a small change.

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
