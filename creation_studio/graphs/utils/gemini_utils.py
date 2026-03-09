import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

_ENV_PATH = Path(__file__).parents[3] / ".env"


def _resolve_key(env_var: str = "GEMINI_API_KEY") -> str:
    """Return API key from os.environ or .env file."""
    key = os.environ.get(env_var, "")
    if key:
        return key
    if _ENV_PATH.exists():
        for line in _ENV_PATH.read_text().splitlines():
            line = line.strip()
            if line.startswith(f"{env_var}="):
                return line.split("=", 1)[1].strip()
    return ""


def call_gemini(prompt: str) -> dict:
    api_key = _resolve_key()
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.5-flash:generateContent?key={api_key}"
    )
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "tools": [{"google_search": {}}],
        "generationConfig": {"maxOutputTokens": 2048, "temperature": 0.3},
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gemini API {e.code}: {body}") from e


def extract_text(response_data: dict) -> str:
    try:
        candidate = response_data.get("candidates", [{}])[0]
        parts = candidate.get("content", {}).get("parts", [])
        return "".join(p.get("text", "") for p in parts)
    except Exception:
        return json.dumps(response_data)


def generate_image(prompt: str) -> str | None:
    """Calls Gemini image generation. Returns base64 PNG string or None."""
    api_key = _resolve_key("GEMINI_IMAGE_API_KEY")
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.5-flash-image:generateContent?key={api_key}"
    )
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            response = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gemini image API {e.code}: {body}") from e

    try:
        parts = response["candidates"][0]["content"]["parts"]
        for part in parts:
            if "inlineData" in part:
                return part["inlineData"]["data"]  # base64 PNG
    except Exception:
        pass
    return None


def edit_image(prompt: str, image_bytes: bytes) -> str | None:
    """Edit an image with Gemini. Returns base64 PNG string or None."""
    import base64

    api_key = _resolve_key("GEMINI_IMAGE_API_KEY")
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.5-flash-image:generateContent?key={api_key}"
    )
    b64_image = base64.b64encode(image_bytes).decode()
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "inlineData": {
                            "mimeType": "image/png",
                            "data": b64_image,
                        }
                    },
                    {"text": prompt},
                ],
            }
        ],
        "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            response = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"Gemini edit_image API {e.code}: {body}")
        return None

    try:
        parts = response["candidates"][0]["content"]["parts"]
        for part in parts:
            if "inlineData" in part:
                return part["inlineData"]["data"]
    except Exception:
        pass
    return None


def call_gemini_vision(prompt: str, image_base64: str, mime_type: str = "image/png") -> dict:
    """Call Gemini with an image + text prompt; returns parsed JSON from the text response."""
    api_key = _resolve_key()
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.5-flash:generateContent?key={api_key}"
    )
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"inlineData": {"mimeType": mime_type, "data": image_base64}},
                    {"text": prompt},
                ],
            }
        ],
        "generationConfig": {"maxOutputTokens": 1024, "temperature": 0.1},
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            response = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gemini vision API {e.code}: {body}") from e
    text = extract_text(response)
    return parse_json(text)


def generate_image_with_logo(
    prompt: str,
    logo_base64: str,
    logo_mime_type: str = "image/png",
    template_base64: str | None = None,
) -> str | None:
    """Generate a branded image using Gemini with logo injected as first part.

    Returns base64 PNG string or None.
    """
    api_key = _resolve_key("GEMINI_IMAGE_API_KEY")
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.5-flash-image:generateContent?key={api_key}"
    )
    parts: list = []
    if logo_base64:
        parts.append({"inlineData": {"mimeType": logo_mime_type, "data": logo_base64}})
    if template_base64:
        parts.append({"inlineData": {"mimeType": "image/png", "data": template_base64}})
    parts.append({"text": prompt})

    payload = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            response = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gemini image-with-logo API {e.code}: {body}") from e

    try:
        parts_out = response["candidates"][0]["content"]["parts"]
        for part in parts_out:
            if "inlineData" in part:
                return part["inlineData"]["data"]
    except Exception:
        pass
    return None


def parse_json(text: str) -> dict:
    try:
        match = re.search(r"```(?:json)?\s*\n?([\s\S]*?)\n?```", text)
        if match:
            return json.loads(match.group(1).strip())
        start = text.find("{")
        if start != -1:
            depth = 0
            for i in range(start, len(text)):
                if text[i] == "{":
                    depth += 1
                elif text[i] == "}":
                    depth -= 1
                if depth == 0:
                    return json.loads(text[start : i + 1])
    except Exception:
        pass
    return {"raw_response": text[:2000]}
