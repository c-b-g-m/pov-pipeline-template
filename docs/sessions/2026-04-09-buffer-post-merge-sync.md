# Session: Sync Public Template with Buffer Post-Merge Flow
**Date:** 2026-04-09

## Context
The private `cazimi-hot-takes-pipeline` repo had recently been updated to move Buffer posting from the pipeline itself to a post-merge GitHub Action on the site repo. The public template (`pov-pipeline-template`) still had the old flow where Buffer was called inline during Step 4 of the pipeline, using the dead v1 REST API.

## Conversation

**User:** We made an update to my repo for this project to separate out the GH --> Buffer flow. Please read through to understand the changes. Next, please update the public repo, the one that does not involve Cazimi Marketing, so that it reflects these changes and will work in that same way for anyone who forks it.

**Assistant:** Explored both repos thoroughly using subagents. Identified the private repo (`cazimi-hot-takes-pipeline`) and the public template (`pov-pipeline-template`). Read all key files in both repos to understand the current state and what needed to change.

Presented a 7-file change plan:
1. `pipeline/main.py` — Remove Buffer import, var, and Step 4
2. `pipeline/buffer_client.py` — Rewrite from v1 REST to GraphQL API
3. `.github/workflows/buffer-on-merge.example.yml` — New post-merge workflow example
4. `.github/workflows/pipeline.yml` — Remove BUFFER_ACCESS_TOKEN env var
5. `config.example.yaml` — Update Buffer section docs
6. `README.md` — Update architecture diagram, add Buffer post-merge section
7. `env.example` — Update Buffer variable descriptions

**User:** Yes, please.

**Assistant:** Executed all changes:
- Removed Buffer import, `buffer_token` variable, and entire Step 4 loop from `main.py`
- Rewrote `buffer_client.py` from v1 REST (`bufferapp.com/1/`) to GraphQL (`api.buffer.com`), generalized with `organization_id` as a param instead of hardcoded
- Created `buffer-on-merge.example.yml` — a ready-to-copy workflow for site repos that triggers on push to main, diffs for new content files, parses `linkedInDraft` from YAML frontmatter, and sends to Buffer GraphQL as a draft
- Removed `BUFFER_ACCESS_TOKEN` from pipeline workflow env vars
- Updated `config.example.yaml` to replace `buffer: enabled: false` with docs about the post-merge approach
- Updated `env.example` to mark Buffer vars as site-repo-only, commented out by default
- Updated `README.md` with new architecture diagram, full "Buffer Integration (Post-Merge)" section with setup steps and flow diagram
- Ran Python syntax checks and YAML validation — all clean

**User:** Yes, please. (to commit)

**Assistant:** Committed: `b80fd33 Move Buffer posting from pipeline to post-merge GitHub Action`

**User:** Yes, please. (to push)

**Assistant:** Pushed to `c-b-g-m/pov-pipeline-template` main branch.

**User:** Please wrap up.

## Files Changed
- `.github/workflows/buffer-on-merge.example.yml` (new)
- `.github/workflows/pipeline.yml` (modified)
- `README.md` (modified)
- `config.example.yaml` (modified)
- `env.example` (modified)
- `pipeline/buffer_client.py` (modified — full rewrite)
- `pipeline/main.py` (modified)
