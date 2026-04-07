"""
Buffer integration — sends social post drafts to Buffer's queue.

EXPERIMENTAL: Buffer's v1 API auth can be finicky. Posts land in
Buffer's queue as drafts — the user approves in the Buffer UI.

Requires BUFFER_ACCESS_TOKEN in .env.
"""

import json
import logging
from typing import Dict, List, Optional
from urllib.error import URLError
from urllib.request import Request, urlopen

log = logging.getLogger(__name__)

BUFFER_API_BASE = "https://api.bufferapp.com/1"


def get_profiles(access_token: str, service: str = "linkedin") -> List[dict]:
    """Fetch Buffer profiles to find the target profile ID."""
    try:
        req = Request(
            f"{BUFFER_API_BASE}/profiles.json?access_token={access_token}",
            headers={"Accept": "application/json"},
        )
        with urlopen(req, timeout=15) as resp:
            profiles = json.loads(resp.read().decode())
            return [p for p in profiles if p.get("service") == service]
    except Exception as e:
        log.error("Failed to fetch Buffer profiles: %s", e)
        return []


def create_draft(
    access_token: str,
    profile_id: str,
    text: str,
    link: Optional[str] = None,
) -> Optional[dict]:
    """
    Create a draft post in Buffer's queue.

    The post will appear as a draft in Buffer — not auto-published.
    The user reviews and approves in the Buffer UI.
    """
    payload = {
        "text": text,
        "profile_ids[]": profile_id,
        "draft": "true",
    }

    if link:
        payload["media[link]"] = link

    body = "&".join(f"{k}={v}" for k, v in payload.items()).encode()

    try:
        req = Request(
            f"{BUFFER_API_BASE}/updates/create.json?access_token={access_token}",
            data=body,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="POST",
        )
        with urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode())
            if result.get("success"):
                log.info("Buffer draft created successfully")
                return result
            else:
                log.error("Buffer API returned failure: %s", result)
                return None
    except Exception as e:
        log.error("Failed to create Buffer draft: %s", e)
        return None


def send_to_buffer(
    access_token: str,
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

    profiles = get_profiles(access_token, service=service)
    if not profiles:
        log.warning("No %s profiles found in Buffer", service)
        return False

    profile_id = profiles[0]["id"]

    text = social_draft
    if site_url:
        text = text.replace("[LINK]", site_url)
        text = text.replace("Link in comments", f"Full take: {site_url}")

    result = create_draft(
        access_token=access_token,
        profile_id=profile_id,
        text=text,
        link=site_url,
    )

    return result is not None
