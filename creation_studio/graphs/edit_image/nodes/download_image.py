import urllib.request

from ..state import EditImageState


def download_image_node(state: EditImageState) -> dict:
    img_url = state.get("img_url", "")
    req = urllib.request.Request(img_url, method="GET")
    with urllib.request.urlopen(req, timeout=60) as resp:
        image_bytes = resp.read()
    return {"image_bytes": image_bytes}
