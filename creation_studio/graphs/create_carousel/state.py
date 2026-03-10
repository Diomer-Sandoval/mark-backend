from typing_extensions import TypedDict


class CarouselPipelineState(TypedDict, total=False):
    # Input
    topic: str
    prompt: str            # mirrors topic — required by reused research nodes
    platform: str          # single platform string e.g. "instagram"
    platforms: list        # [platform] — required by reused research nodes
    post_tone: str
    num_slides: int
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

    # Carousel outputs
    carousel_strategy: dict   # {slides, visual_theme, caption, hashtags}
    template_context: str
    caption: str
    hashtags: list
    completed_slides: list    # list of CompletedSlide dicts
