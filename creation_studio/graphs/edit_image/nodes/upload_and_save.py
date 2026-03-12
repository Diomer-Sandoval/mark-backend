import uuid as _uuid_lib

from ..state import EditImageState
from ...utils.cloudinary_utils import upload_image


def upload_and_save_node(state: EditImageState) -> dict:
    edited_base64 = state.get("edited_image_base64", "")
    if not edited_base64:
        return {"result_url": "", "generation_uuid": ""}

    generation_uuid = str(_uuid_lib.uuid4())
    creation_uuid = state.get("creation_uuid", "")

    result_url = upload_image(
        base64_data=edited_base64,
        folder=f"ia_generations/{creation_uuid}",
        public_id=generation_uuid,
    )

    return {"result_url": result_url, "generation_uuid": generation_uuid}
