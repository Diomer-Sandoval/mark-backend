import base64
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

_ENV_PATH = Path(__file__).parents[3] / ".env"

_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

_POLL_INTERVAL = 5    # seconds between polls
_MAX_POLLS = 150      # ~12.5 minutes max


def _resolve_key(env_var: str) -> str:
    key = os.environ.get(env_var, "")
    if key:
        return key
    if _ENV_PATH.exists():
        for line in _ENV_PATH.read_text().splitlines():
            line = line.strip()
            if line.startswith(f"{env_var}="):
                return line.split("=", 1)[1].strip()
    return ""


def _api_key() -> str:
    return _resolve_key("GEMINI_IMAGE_API_KEY")


def generate_video_scene(
    prompt: str,
    aspect_ratio: str = "9:16",
    duration: int = 6,
) -> str | None:
    """Submit a scene to Veo, poll until done, return base64-encoded MP4 or None if filtered."""
    api_key = _api_key()

    # ── Submit — try multiple model + body combos (mirrors n8n workflow) ─────
    body_with_params = {
        "instances": [{"prompt": prompt}],
        "parameters": {"aspectRatio": aspect_ratio, "generateAudio": False},
    }
    body_minimal = {
        "instances": [{"prompt": prompt}],
        "parameters": {"generateAudio": False},
    }
    body_bare = {
        "instances": [{"prompt": prompt}],
    }

    attempts_list = [
        {"model": "veo-3.0-generate-preview", "body": body_with_params},
        {"model": "veo-3.0-generate-preview", "body": body_minimal},
        {"model": "veo-3.0-generate-001",     "body": body_minimal},
        {"model": "veo-3.0-generate-001",     "body": body_bare},
        {"model": "veo-2.0-generate-001",     "body": body_minimal},
    ]

    operation_name = None
    last_error = ""

    for attempt in attempts_list:
        url = f"{_BASE}/{attempt['model']}:predictLongRunning?key={api_key}"
        data = json.dumps(attempt["body"]).encode()
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                response = json.loads(resp.read())
            operation_name = response.get("name")
            break
        except urllib.error.HTTPError as e:
            last_error = f"{attempt['model']}: HTTP {e.code}"
            if e.code in (400, 403, 404):
                continue
            body_err = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Veo submit error {e.code}: {body_err}") from e

    if not operation_name:
        raise RuntimeError(
            f"Veo: all model+body combinations failed. Last error: {last_error}. "
            "Ensure GEMINI_IMAGE_API_KEY is set and has Veo access."
        )

    # ── Poll ──────────────────────────────────────────────────────────────────
    poll_url = f"https://generativelanguage.googleapis.com/v1beta/{operation_name}?key={api_key}"
    poll_result = None

    for _ in range(_MAX_POLLS):
        time.sleep(_POLL_INTERVAL)
        req = urllib.request.Request(
            poll_url,
            headers={"x-goog-api-key": api_key},
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                poll_result = json.loads(resp.read())
        except Exception:
            continue

        if poll_result.get("done"):
            break
        if poll_result.get("error"):
            raise RuntimeError(f"Veo generation error: {poll_result['error']}")
    else:
        raise RuntimeError("Veo generation timed out after ~12 minutes")

    # ── Extract ───────────────────────────────────────────────────────────────
    video_response = (poll_result or {}).get("response", {}).get("generateVideoResponse", {})
    samples = video_response.get("generatedSamples", [])

    if not samples:
        if video_response.get("raiMediaFilteredCount", 0) > 0:
            return None  # filtered by safety — caller handles this
        raise RuntimeError(
            f"Veo: no samples returned. Full response: {json.dumps(poll_result or {})[:400]}"
        )

    video_uri = samples[0].get("video", {}).get("uri")
    if not video_uri:
        raise RuntimeError("Veo: video URI missing from response")

    # ── Download ──────────────────────────────────────────────────────────────
    sep = "&" if "?" in video_uri else "?"
    download_url = f"{video_uri}{sep}key={api_key}"
    req = urllib.request.Request(
        download_url,
        headers={"x-goog-api-key": api_key},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        video_bytes = resp.read()

    return base64.b64encode(video_bytes).decode()
