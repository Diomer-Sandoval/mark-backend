from ..state import EditImageState
from ...utils.gemini_utils import edit_image


def edit_with_gemini_node(state: EditImageState) -> dict:
    result = edit_image(
        prompt=state.get("prompt", ""),
        image_bytes=state.get("image_bytes", b""),
    )
    if result is None:
        return {"gemini_failed": True}
    return {"edited_image_base64": result, "gemini_failed": False}
