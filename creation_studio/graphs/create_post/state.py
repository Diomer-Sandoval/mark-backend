from typing_extensions import TypedDict


class ContentPipelineState(TypedDict, total=False):
    # ── Input fields ──────────────────────────────────────────────
    company: str
    topic: str
    platform: str
    post_type: str
    post_tone: str
    brand_tone: str
    brand_dna: dict
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
