import json
import os
import urllib.error
import urllib.request
from pathlib import Path

_ENV_PATH = Path(__file__).parents[3] / ".env"


def _resolve_key(env_var: str = "OPENAI_API_KEY") -> str:
    key = os.environ.get(env_var, "")
    if key:
        return key
    if _ENV_PATH.exists():
        for line in _ENV_PATH.read_text().splitlines():
            line = line.strip()
            if line.startswith(f"{env_var}="):
                return line.split("=", 1)[1].strip()
    return ""


def edit_image(prompt: str, image_bytes: bytes) -> str | None:
    """Edit an image using OpenAI gpt-image-1. Returns base64 PNG or None."""
    import base64

    api_key = _resolve_key()
    url = "https://api.openai.com/v1/images/edits"

    b64_image = base64.b64encode(image_bytes).decode()

    # OpenAI images/edits expects multipart form data
    boundary = "----FormBoundary7MA4YWxkTrZu0gW"
    body_parts = []

    # model field
    body_parts.append(f"--{boundary}")
    body_parts.append('Content-Disposition: form-data; name="model"')
    body_parts.append("")
    body_parts.append("gpt-image-1")

    # prompt field
    body_parts.append(f"--{boundary}")
    body_parts.append('Content-Disposition: form-data; name="prompt"')
    body_parts.append("")
    body_parts.append(prompt)

    # image field as base64 PNG file
    body_parts.append(f"--{boundary}")
    body_parts.append(
        'Content-Disposition: form-data; name="image"; filename="image.png"'
    )
    body_parts.append("Content-Type: image/png")
    body_parts.append("")

    # Build body with binary image data
    text_before_image = "\r\n".join(body_parts) + "\r\n"
    text_after_image = (
        f"\r\n--{boundary}\r\n"
        'Content-Disposition: form-data; name="response_format"\r\n'
        "\r\n"
        "b64_json\r\n"
        f"--{boundary}--\r\n"
    )

    body = (
        text_before_image.encode()
        + image_bytes
        + text_after_image.encode()
    )

    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            response = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        print(f"OpenAI image edit API {e.code}: {error_body}")
        return None

    try:
        return response["data"][0]["b64_json"]
    except (KeyError, IndexError):
        return None
