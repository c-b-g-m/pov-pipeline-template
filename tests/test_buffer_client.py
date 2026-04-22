"""Tests for pipeline/buffer_client.py."""

import pytest
import pipeline.buffer_client as buffer_client


def _graphql_channels(channels):
    return lambda *a, **kw: {"data": {"channels": channels}}


# ─── get_channel ─────────────────────────────────────────────────────────────

def test_get_channel_returns_id_for_matching_service(monkeypatch):
    channels = [
        {"id": "ch-li-123", "service": "linkedin", "isDisconnected": False},
        {"id": "ch-tw-456", "service": "twitter", "isDisconnected": False},
    ]
    monkeypatch.setattr(buffer_client, "_graphql", _graphql_channels(channels))
    result = buffer_client.get_channel("tok", "org123")
    assert result == "ch-li-123"


def test_get_channel_skips_disconnected(monkeypatch):
    channels = [
        {"id": "ch-li-123", "service": "linkedin", "isDisconnected": True},
    ]
    monkeypatch.setattr(buffer_client, "_graphql", _graphql_channels(channels))
    result = buffer_client.get_channel("tok", "org123")
    assert result is None


def test_get_channel_service_not_found_returns_none(monkeypatch):
    channels = [{"id": "ch-tw-456", "service": "twitter", "isDisconnected": False}]
    monkeypatch.setattr(buffer_client, "_graphql", _graphql_channels(channels))
    result = buffer_client.get_channel("tok", "org123", service="linkedin")
    assert result is None


def test_get_channel_exception_returns_none(monkeypatch):
    def raise_exc(*a, **kw):
        raise ConnectionError("network error")
    monkeypatch.setattr(buffer_client, "_graphql", raise_exc)
    result = buffer_client.get_channel("tok", "org123")
    assert result is None


# ─── create_draft ─────────────────────────────────────────────────────────────

def test_create_draft_success(monkeypatch):
    response = {"data": {"createPost": {"post": {"id": "post-abc", "text": "Hello"}}}}
    monkeypatch.setattr(buffer_client, "_graphql", lambda *a, **kw: response)
    result = buffer_client.create_draft("tok", "ch-123", "Hello")
    assert result == {"id": "post-abc", "text": "Hello"}


def test_create_draft_api_error_returns_none(monkeypatch):
    response = {"data": {"createPost": {"message": "Unauthorized"}}}
    monkeypatch.setattr(buffer_client, "_graphql", lambda *a, **kw: response)
    result = buffer_client.create_draft("tok", "ch-123", "Hello")
    assert result is None


def test_create_draft_exception_returns_none(monkeypatch):
    def raise_exc(*a, **kw):
        raise ConnectionError("network error")
    monkeypatch.setattr(buffer_client, "_graphql", raise_exc)
    result = buffer_client.create_draft("tok", "ch-123", "Hello")
    assert result is None


# ─── send_to_buffer ──────────────────────────────────────────────────────────

def test_send_to_buffer_no_token_returns_false(monkeypatch):
    result = buffer_client.send_to_buffer("", "org123", "Some post text")
    assert result is False


def test_send_to_buffer_no_org_id_returns_false(monkeypatch):
    result = buffer_client.send_to_buffer("token", "", "Some post text")
    assert result is False


def test_send_to_buffer_link_placeholder_replaced(monkeypatch):
    captured = {}

    def fake_get_channel(*a, **kw):
        return "ch-123"

    def fake_create_draft(access_token, channel_id, text):
        captured["text"] = text
        return {"id": "post-1", "text": text}

    monkeypatch.setattr(buffer_client, "get_channel", fake_get_channel)
    monkeypatch.setattr(buffer_client, "create_draft", fake_create_draft)

    buffer_client.send_to_buffer("tok", "org123", "Read more at [LINK]", site_url="https://example.com/pov/slug/")
    assert "https://example.com/pov/slug/" in captured["text"]
    assert "[LINK]" not in captured["text"]


def test_send_to_buffer_returns_true_on_success(monkeypatch):
    monkeypatch.setattr(buffer_client, "get_channel", lambda *a, **kw: "ch-123")
    monkeypatch.setattr(buffer_client, "create_draft", lambda *a, **kw: {"id": "post-1", "text": "hi"})
    result = buffer_client.send_to_buffer("tok", "org123", "Post text")
    assert result is True


def test_send_to_buffer_returns_false_when_channel_not_found(monkeypatch):
    monkeypatch.setattr(buffer_client, "get_channel", lambda *a, **kw: None)
    result = buffer_client.send_to_buffer("tok", "org123", "Post text")
    assert result is False
