import json
from unittest.mock import Mock, patch

import pytest

from pipeline import ContentPipeline, InputError, _extract_json, validate_public_url

def valid_payload():
    return {
        "blog_title": "A useful title",
        "blog_meta_description": "A short description",
        "blog_post": "## Introduction\n\nA helpful article.",
        "tweets": [f"Post number {i}" for i in range(1, 6)],
        "linkedin_post": "A professional LinkedIn post.",
        "key_points": ["One", "Two", "Three"],
    }

def test_extract_json_from_markdown_fence():
    assert _extract_json("```json\n" + json.dumps(valid_payload()) + "\n```")["blog_title"] == "A useful title"

def test_topic_generation_returns_structured_package():
    client = Mock()
    client.messages.create.return_value.content = [Mock(type="text", text=json.dumps(valid_payload()))]
    pipeline = ContentPipeline(api_key="test-key", client=client, sleep=lambda _: None)
    result = pipeline.generate("topic", "How small businesses can use social media", "SMEs", "Friendly")
    assert len(result["tweets"]) == 5
    assert result["blog_title"] == "A useful title"
    assert "not independently web-researched" in result["source_note"]

def test_missing_topic_is_rejected_before_api_call():
    client = Mock()
    pipeline = ContentPipeline(api_key="test-key", client=client)
    with pytest.raises(InputError):
        pipeline.generate("topic", " ", "SMEs", "Friendly")
    client.messages.create.assert_not_called()

def test_incomplete_ai_output_is_rejected():
    client = Mock()
    client.messages.create.return_value.content = [Mock(type="text", text='{"blog_title":"Only title"}')]
    pipeline = ContentPipeline(api_key="test-key", client=client)
    with pytest.raises(Exception):
        pipeline.generate("topic", "A meaningful topic", "SMEs", "Friendly")

def test_localhost_url_is_rejected():
    with pytest.raises(InputError):
        validate_public_url("http://localhost:5000/private")

def test_invalid_url_scheme_is_rejected():
    with pytest.raises(InputError):
        validate_public_url("file:///etc/passwd")
