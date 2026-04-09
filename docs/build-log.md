# Build Log — pov-pipeline-template

## 2026-04-09: Buffer post-merge sync

**What was built:**
- Synced public template with private repo's Buffer post-merge architecture
- Removed inline Buffer posting from pipeline (was Step 4 in main.py)
- Rewrote `buffer_client.py` from dead v1 REST API to GraphQL
- Created `buffer-on-merge.example.yml` — ready-to-copy post-merge workflow for site repos
- Updated README with full Buffer integration docs, setup steps, and flow diagram
- Updated config.example.yaml, env.example, and pipeline.yml to reflect new flow

**What broke:** Nothing — clean syntax checks, pushed successfully.

**Tech debt:** None introduced.

**Commit:** `b80fd33` pushed to `c-b-g-m/pov-pipeline-template` main.
