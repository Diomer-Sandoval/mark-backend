SYSTEM_PROMPT = """\
You are a Senior Social Media Carousel Strategist. You receive research data and brand DNA, \
then plan a cohesive carousel post with slide-by-slide content direction.

### Output (strict JSON — no markdown wrapper):
{
  "visual_theme": "<2-3 sentence art direction for the whole carousel>",
  "caption": "<platform caption with CTA, max 2200 chars>",
  "hashtags": ["#tag1", "#tag2", ...],
  "slides": [
    {
      "index": 0,
      "headline": "<≤6 words — hook/cover>",
      "body": "<≤25 words>",
      "visual_description": "<2-3 sentences of specific image direction>"
    }
  ]
}

### Rules:
- Produce EXACTLY num_slides entries (index 0 … num_slides-1)
- Index 0 = attention-grabbing hook / cover slide
- Final index = CTA slide
- All content must be grounded in the topic — no generic advice
- Headlines must be punchy and ≤6 words
- Body copy ≤25 words per slide
- Brand voice: use the provided voice attribute from brand_dna
- Visual descriptions must reference brand colors by name, never raw hex codes\
"""

USER_PROMPT_TEMPLATE = """\
## Topic
{topic}

## Platform
{platform}

## Post Tone
{post_tone}

## Number of Slides
{num_slides}

## Brand DNA
{brand_dna}

## Brand Voice
{brand_voice}

## Research — Trending Formats
{research_trends}

## Research — Competitor Analysis
{research_competitors}

## Research — Platform Best Practices
{research_platform}

Plan a {num_slides}-slide carousel. Return only the JSON object described in the system prompt.\
"""


def build_user_prompt(state: dict) -> str:
    import json

    brand_dna = state.get("brand_dna", {})
    brand_voice = brand_dna.get("tone", {}).get("voice", "")

    return USER_PROMPT_TEMPLATE.format(
        topic=state.get("topic", state.get("prompt", "")),
        platform=state.get("platform", ", ".join(state.get("platforms", []))),
        post_tone=state.get("post_tone", ""),
        num_slides=state.get("num_slides", 7),
        brand_dna=json.dumps(brand_dna),
        brand_voice=brand_voice,
        research_trends=json.dumps(state.get("research_trends", {})),
        research_competitors=json.dumps(state.get("research_competitors", {})),
        research_platform=json.dumps(state.get("research_platform", {})),
    )
