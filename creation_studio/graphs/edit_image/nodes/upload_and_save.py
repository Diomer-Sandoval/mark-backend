import random
import string

from ..state import EditImageState
from ...utils.cloudinary_utils import upload_image


def _make_uuid(length: int = 17) -> str:
    chars = string.ascii_letters + string.digits
    return "".join(random.choices(chars, k=length))


def upload_and_save_node(state: EditImageState) -> dict:
    edited_base64 = state.get("edited_image_base64", "")
    if not edited_base64:
        return {"result_url": "", "generation_uuid": ""}

    generation_uuid = _make_uuid()
    creation_uuid = state.get("creation_uuid", "")

    result_url = upload_image(
        base64_data=edited_base64,
        folder=f"ia_generations/{creation_uuid}",
        public_id=generation_uuid,
    )

    return {"result_url": result_url, "generation_uuid": generation_uuid}
