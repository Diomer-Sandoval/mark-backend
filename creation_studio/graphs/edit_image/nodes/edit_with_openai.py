from ..state import EditImageState
from ...utils.openai_utils import edit_image


def edit_with_openai_node(state: EditImageState) -> dict:
    result = edit_image(
        prompt=state.get("prompt", ""),
        image_bytes=state.get("image_bytes", b""),
    )
    if result is None:
        return {"edited_image_base64": ""}
    return {"edited_image_base64": result}
