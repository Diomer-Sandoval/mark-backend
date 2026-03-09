from typing_extensions import TypedDict


class VideoPipelineState(TypedDict, total=False):
    # Input
    topic: str
    prompt: str            # mirrors topic — required by reused research nodes
    platform: str
    platforms: list        # [platform] — required by reused research nodes
    video_tone: str
    num_scenes: int
    scene_duration: int    # seconds per scene
    aspect_ratio: str      # "9:16", "16:9", "1:1"
    brand_dna: dict
    identity: dict
    logo_base64: str
    logo_mime_type: str

    # Research (same field names as ContentPipelineState so nodes are reusable)
    research_trends: dict
    research_competitors: dict
    research_platform: dict

    # Job ID
    creation_uuid: str

    # Video outputs
    video_strategy: dict   # {scenes, visual_theme, caption, hashtags, video_strategy}
    template_context: str
    caption: str
    hashtags: list
    completed_scenes: list  # list of CompletedScene dicts
