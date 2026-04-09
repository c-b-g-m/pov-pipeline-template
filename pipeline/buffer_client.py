"""
Buffer integration — sends social post drafts to Buffer's queue.

Uses Buffer's GraphQL API (https://api.buffer.com) to create draft posts.
Posts land in Buffer's queue as drafts — the user approves in the Buffer UI.

NOTE: This module is NOT called by the pipeline itself. It exists as a
utility for the post-merge GitHub Action (buffer-on-merge.yml) that runs
in your site repo. The pipeline creates PRs with the social draft in
frontmatter; the post-merge action reads the merged content and sends it
to Buffer — ensuring only reviewed/edited content reaches social.

Requires BUFFER_ACCESS_TOKEN and BUFFER_ORGANIZATION_ID in environment.
"""

import json
import logging
from typing import Optional
from urllib.request import Request, urlopen

log = logging.getLogger(__name__)

BUFFER_API = "https://api.buffer.com"


def _graphql(access_token: str, query: str, variables: Optional[dict] = None) -> dict:
    """Execute a GraphQL request against Buffer's API."""
    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    body = json.dumps(payload).encode()
    req = Request(
        BUFFER_API,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
            "User-Agent": "pov-pipeline/1.0",
        },
        method="POST",
    )
    with urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def get_channel(access_token: str, organization_id: str, service: str = "linkedin") -> Optional[str]:
    """Fetch a channel ID from Buffer by service name."""
    query = """
    query GetChannels($input: ChannelsInput!) {
        channels(input: $input) {
            id
            name
            service
            isDisconnected
        }
    }
    """
    variables = {"input": {"organizationId": organization_id}}

    try:
        result = _graphql(access_token, query, variables)
        channels = result.get("data", {}).get("channels", [])
        for ch in channels:
            if ch.get("service", "").lower() == service and not ch.get("isDisconnected"):
                return ch["id"]
        log.warning("No connected %s channel found in Buffer", service)
        return None
    except Exception as e:
        log.error("Failed to fetch Buffer channels: %s", e)
        return None


def create_draft(
    access_token: str,
    channel_id: str,
    text: str,
) -> Optional[dict]:
    """
    Create a draft post in Buffer's queue.

    The post will appear as a draft in Buffer — not auto-published.
    The user reviews and approves in the Buffer UI.
    """
    query = """
    mutation CreatePost($input: CreatePostInput!) {
        createPost(input: $input) {
            ... on PostActionSuccess {
                post {
                    id
                    text
                }
            }
            ... on MutationError {
                message
            }
        }
    }
    """
    variables = {
        "input": {
            "text": text,
            "channelId": channel_id,
            "schedulingType": "automatic",
            "mode": "addToQueue",
            "saveToDraft": True,
        }
    }

    try:
        result = _graphql(access_token, query, variables)
        data = result.get("data", {}).get("createPost", {})

        if "post" in data:
            log.info("Buffer draft created successfully (ID: %s)", data["post"]["id"])
            return data["post"]

        error_msg = data.get("message", result.get("errors", "Unknown error"))
        log.error("Buffer API error: %s", error_msg)
        return None
    except Exception as e:
        log.error("Failed to create Buffer draft: %s", e)
        return None


def send_to_buffer(
    access_token: str,
    organization_id: str,
    social_draft: str,
    site_url: Optional[str] = None,
    service: str = "linkedin",
) -> bool:
    """
    Send a social draft to Buffer.

    Returns True on success, False on failure.
    Fails gracefully — Buffer is optional, not blocking.
    """
    if not access_token:
        log.info("No BUFFER_ACCESS_TOKEN — skipping Buffer")
        return False

    if not organization_id:
        log.error("No BUFFER_ORGANIZATION_ID — skipping Buffer")
        return False

    channel_id = get_channel(access_token, organization_id, service=service)
    if not channel_id:
        return False

    # Replace [LINK] placeholder with actual URL if available
    text = social_draft
    if site_url:
        text = text.replace("[LINK]", site_url)
        text = text.replace("Link in comments", f"Full take: {site_url}")

    result = create_draft(
        access_token=access_token,
        channel_id=channel_id,
        text=text,
    )

    return result is not None
