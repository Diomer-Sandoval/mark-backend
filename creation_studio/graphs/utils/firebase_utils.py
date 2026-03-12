"""
Utility functions for creating and updating models in the graph.
(Previously Firebase-based, now using Django models).
"""
import logging
import json

logger = logging.getLogger(__name__)

_STATUS_MAP = {
    "active": "done",
    "pending": "pending",
    "in_progress": "in_progress",
    "done": "done",
    "failed": "failed",
    "cancelled": "cancelled",
}


def create_creation(creation_uuid: str, data: dict) -> None:
    from creation_studio.models.core import Creation

    platforms = data.get("platforms", [])
    if isinstance(platforms, list):
        platforms = ",".join(str(p) for p in platforms)

    post_type = data.get("post_type") or data.get("type") or "post"
    valid_post_types = {c[0] for c in Creation.POST_TYPE_CHOICES}
    if post_type not in valid_post_types:
        post_type = "post"

    status = _STATUS_MAP.get(data.get("status", "pending"), "pending")
    title = (
        data.get("topic", "")
        or data.get("title", "")
        or str(creation_uuid)[:50]
    )
    post_tone = data.get("post_tone", "") or data.get("video_tone", "")

    try:
        Creation.objects.create(
            uuid=creation_uuid,
            brand=None, # Brand assignment happens in views if brand_uuid is provided
            title=title,
            post_type=post_type,
            status=status,
            platforms=platforms,
            post_tone=post_tone,
        )
    except Exception as exc:
        logger.error("Failed to create Creation %s: %s", creation_uuid, exc)


def create_generation(creation_uuid: str, generation_uuid: str, data: dict) -> None:
    from creation_studio.models.core import Creation, Generation

    try:
        creation = Creation.objects.get(uuid=creation_uuid)
    except Creation.DoesNotExist:
        logger.error(
            "Creation %s not found — skipping generation %s",
            creation_uuid,
            generation_uuid,
        )
        return

    parent = None
    parent_uuid = data.get("parent_uuid")
    if parent_uuid and parent_uuid != creation_uuid:
        try:
            parent = Generation.objects.get(uuid=parent_uuid)
        except Generation.DoesNotExist:
            pass

    # New model uses 'type' instead of 'media_type'
    gen_type = data.get("type", "image")
    if data.get("video_url"):
        gen_type = "video"
    elif data.get("img_url"):
        gen_type = "image"
        
    status = _STATUS_MAP.get(data.get("status", "done"), "done")

    # The new model has 'content' instead of 'generation_params'
    # We'll store the main content (URL or copy) in the content field.
    content = data.get("content", "")
    if not content:
        content = data.get("img_url", "") or data.get("video_url", "") or data.get("copy", "")
    
    # If there's still more data, we could potentially JSON-ify it into content,
    # but the model says it's for 'Generated content output'.
    # For now, let's keep it simple.

    try:
        Generation.objects.create(
            uuid=generation_uuid,
            creation=creation,
            parent=parent,
            type=gen_type,
            prompt=data.get("prompt", ""),
            status=status,
            content=content,
        )
    except Exception as exc:
        logger.error("Failed to create Generation %s: %s", generation_uuid, exc)


def update_creation(creation_uuid: str, data: dict) -> None:
    from creation_studio.models.core import Creation

    try:
        creation = Creation.objects.get(uuid=creation_uuid)
    except Creation.DoesNotExist:
        logger.warning("Creation %s not found for update", creation_uuid)
        return

    if "status" in data:
        creation.status = _STATUS_MAP.get(data["status"], creation.status)

    if "title" in data:
        creation.title = data["title"]
        
    if "platforms" in data:
        platforms = data["platforms"]
        if isinstance(platforms, list):
            platforms = ",".join(str(p) for p in platforms)
        creation.platforms = platforms

    creation.save()
