import uuid as _uuid_lib

from ...state import ContentPipelineState
from ....utils.gemini_utils import generate_image
from ....utils.cloudinary_utils import upload_image


def generate_image_node(state: ContentPipelineState) -> dict:
    image_base64 = generate_image(state.get("image_prompt", ""))
    if not image_base64:
        return {"image_url": "", "generation_uuid": ""}

    generation_uuid = str(_uuid_lib.uuid4())
    creation_uuid = state.get("creation_uuid", "")

    image_url = upload_image(
        base64_data=image_base64,
        folder=f"ia_generations/{creation_uuid}",
        public_id=generation_uuid,
    )

    return {"image_url": image_url, "generation_uuid": generation_uuid}
