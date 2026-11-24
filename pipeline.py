import ipaddress
import json
import logging
import os
import random
import socket
import time
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class InputError(ValueError):
    """Raised when the submitted topic or URL is invalid."""

class PipelineError(RuntimeError):
    """Raised when source extraction or AI generation fails."""

def validate_public_url(url):
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise InputError("Enter a complete public http:// or https:// URL.")
    if parsed.username or parsed.password:
        raise InputError("URLs containing usernames or passwords are not allowed.")
    host = parsed.hostname.lower()
    if host in {"localhost"} or host.endswith(".localhost") or host.endswith(".local"):
        raise InputError("Local network URLs are not allowed.")
    try:
        addresses = socket.getaddrinfo(host, None)
    except socket.gaierror:
        raise InputError("The website address could not be found.")
    for item in addresses:
        ip = ipaddress.ip_address(item[4][0])
        if not ip.is_global:
            raise InputError("Private or local network URLs are not allowed.")
    return url

def extract_url_text(url, timeout=15, max_chars=12000):
    validate_public_url(url)
    try:
        response = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": "ContentPipelineBot/1.0 (content extraction)"},
            allow_redirects=False,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise PipelineError("Could not retrieve that page. Check the URL and try again.") from exc

    content_type = response.headers.get("Content-Type", "").lower()
    if "text/html" not in content_type:
        raise InputError("That URL does not appear to be an HTML webpage.")
    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript", "form"]):
        tag.decompose()
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    main = soup.find("article") or soup.find("main") or soup.body or soup
    text = " ".join(main.stripped_strings)
    text = " ".join(text.split())
    if len(text) < 150:
        raise InputError("Not enough readable page content was found. Try another URL or paste the topic instead.")
    return f"Page title: {title}\nSource URL: {url}\nPage content:\n{text[:max_chars]}"

def _extract_json(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("AI response did not contain a JSON object.")
    return json.loads(text[start:end + 1])

class ContentPipeline:
    def __init__(self, api_key=None, model="claude-haiku-4-5-20251001",
                 max_retries=3, client=None, sleep=time.sleep):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self.model = model
        self.max_retries = max(1, min(int(max_retries), 5))
        self.client = client
        self.sleep = sleep

    def _get_client(self):
        if self.client is not None:
            return self.client
        if not self.api_key:
            raise PipelineError("AI service is not configured. Add ANTHROPIC_API_KEY to your environment.")
        try:
            import anthropic
        except ImportError as exc:
            raise PipelineError("Anthropic SDK is missing. Install requirements.txt first.") from exc
        self.client = anthropic.Anthropic(api_key=self.api_key, timeout=45.0, max_retries=0)
        return self.client

    def generate(self, source_type, value, audience, tone):
        if source_type == "topic":
            if len(value.strip()) < 3:
                raise InputError("Please enter a more descriptive topic.")
            source_text = f"Topic supplied by the user: {value.strip()}\nNo source article was supplied. Do not invent statistics, quotes, or citations."
            source_note = "Generated from the supplied topic and the model's existing knowledge; not independently web-researched."
        elif source_type == "url":
            source_text = extract_url_text(value.strip())
            source_note = "Based on the readable text extracted from the supplied webpage. Verify important claims against the original source."
        else:
            raise InputError("Unsupported input type.")

        prompt = f"""
Create a useful, original social content package for a marketing agency.

Audience: {audience}
Tone: {tone}

Source material:
{source_text}

Return ONLY valid JSON with this exact structure:
{{
  "blog_title": "A clear, compelling title",
  "blog_meta_description": "One sentence, maximum 155 characters",
  "blog_post": "A well-structured blog post in Markdown, around 500-700 words, with a short introduction, useful H2 sections, practical examples, and a conclusion. Do not fabricate facts or sources.",
  "tweets": [
    "Tweet 1, concise and standalone",
    "Tweet 2, concise and standalone",
    "Tweet 3, concise and standalone",
    "Tweet 4, concise and standalone",
    "Tweet 5, concise and standalone"
  ],
  "linkedin_post": "A polished LinkedIn post with a strong opening, readable short paragraphs, and a relevant call to action.",
  "key_points": ["Key point 1", "Key point 2", "Key point 3"],
  "source_note": "{source_note}"
}}

Make the five tweets distinct in angle, not simple rewrites. Avoid unsupported claims, fake statistics, fake quotations, and fabricated citations. Keep the output appropriate for the audience and tone.
"""
        client = self._get_client()
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                message = client.messages.create(
                    model=self.model,
                    max_tokens=3500,
                    
                    messages=[{"role": "user", "content": prompt}],
                )
                text = "".join(
                    block.text for block in message.content if getattr(block, "type", "") == "text"
                )
                result = _extract_json(text)
                self._validate_result(result)
                result["source_note"] = source_note
                return result
            except Exception as exc:
                # Retry transient network, rate-limit and server failures only.
                error_name = type(exc).__name__
                status_code = getattr(exc, "status_code", None)
                transient = error_name in {
                    "RateLimitError", "APIConnectionError", "APITimeoutError",
                    "InternalServerError"
                } or (isinstance(status_code, int) and status_code >= 500)
                if transient:
                    last_error = exc
                    logger.warning("Temporary AI error on attempt %s/%s: %s",
                                   attempt, self.max_retries, error_name)
                    if attempt < self.max_retries:
                        delay = min(8, 2 ** (attempt - 1)) + random.uniform(0, 0.25)
                        self.sleep(delay)
                        continue
                    break
                if isinstance(exc, (ValueError, KeyError, TypeError)):
                    logger.exception("Invalid AI response")
                    raise PipelineError("The AI returned an incomplete response. Please try again.") from exc
                if status_code is not None:
                    logger.exception("Non-retryable AI API error")
                    raise PipelineError("The AI service rejected the request. Check API configuration and account credits.") from exc
                logger.exception("Unexpected generation failure")
                raise PipelineError("Content generation failed. Please try again.") from exc
        logger.error("AI generation exhausted retries")
        raise PipelineError("The AI service is temporarily unavailable after several attempts. Please try again later.") from last_error

    @staticmethod
    def _validate_result(result):
        required = {"blog_title", "blog_meta_description", "blog_post",
                    "tweets", "linkedin_post", "key_points"}
        if not isinstance(result, dict) or not required.issubset(result):
            raise ValueError("Missing required content fields.")
        if not isinstance(result["tweets"], list) or len(result["tweets"]) != 5:
            raise ValueError("Exactly five tweets are required.")
        if not all(isinstance(result[k], str) and result[k].strip()
                   for k in ["blog_title", "blog_post", "linkedin_post"]):
            raise ValueError("Required content fields must be non-empty text.")
        if not isinstance(result["key_points"], list):
            raise ValueError("Key points must be a list.")
