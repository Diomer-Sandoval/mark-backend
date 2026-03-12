from typing_extensions import TypedDict


class ContentPipelineState(TypedDict, total=False):
    # ── Input fields (mirror the request body) ───────────────────
    prompt: str          # user's content idea, e.g. "A chocolate bar with pepper"
    current_copy: str    # existing copy to improve
    copy_feedback: str   # instructions on what to change, e.g. "make it funnier"
    platforms: list      # e.g. ["instagram", "facebook"]
    post_type: str       # "post", "reel", "story", …
    post_tone: str       # "promotional", "educational", …
    brand_dna: dict      # {color_palette, typography, tone}
    identity: dict       # {logo_url, name, slug, site_url}
    refresh_research: bool # whether to force fresh research even if current_copy exists

    # ── Research results (written by the 3 parallel agents) ───────
    research_trends: dict
    research_competitors: dict
    research_platform: dict

    # ── Job identifiers ───────────────────────────────────────────
    creation_uuid: str
    generation_uuid: str

    # ── Sequential agent outputs ──────────────────────────────────
    strategy: str
    image_prompt: str
    image_url: str
