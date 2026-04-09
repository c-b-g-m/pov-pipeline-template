# Knowledge Base — pov-pipeline-template

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
