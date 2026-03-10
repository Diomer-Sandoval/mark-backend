import logging

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
        or data.get("original_prompt", "")
        or str(creation_uuid)[:50]
    )
    post_tone = data.get("post_tone", "") or data.get("video_tone", "")

    skip_keys = {
        "uuid", "status", "platforms", "post_type", "type",
        "post_tone", "video_tone", "update_at", "creation_at",
    }
    research_data = {k: v for k, v in data.items() if k not in skip_keys}

    try:
        Creation.objects.create(
            uuid=creation_uuid,
            brand=None,
            title=title,
            post_type=post_type,
            status=status,
            platforms=platforms,
            post_tone=post_tone,
            original_prompt=title,
            research_data=research_data,
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

    media_type = "video" if data.get("video_url") else "image"
    status = _STATUS_MAP.get(data.get("status", "done"), "done")

    skip_keys = {"uuid", "creation_uuid", "parent_uuid", "prompt", "status", "create_at"}
    generation_params = {k: v for k, v in data.items() if k not in skip_keys}

    try:
        Generation.objects.create(
            uuid=generation_uuid,
            creation=creation,
            parent=parent,
            media_type=media_type,
            prompt=data.get("prompt", ""),
            status=status,
            generation_params=generation_params,
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

    extra = {k: v for k, v in data.items() if k not in ("status", "update_at")}
    if extra:
        research_data = creation.research_data or {}
        research_data.update(extra)
        creation.research_data = research_data

    creation.save()
