from typing_extensions import TypedDict


class EditImageState(TypedDict, total=False):
    creation_uuid: str
    parent_uuid: str
    prompt: str
    img_url: str
    image_bytes: bytes
    edited_image_base64: str
    generation_uuid: str
    result_url: str
    gemini_failed: bool
