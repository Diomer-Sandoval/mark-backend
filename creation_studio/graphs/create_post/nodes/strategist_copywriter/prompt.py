SYSTEM_PROMPT = """\
You are a Senior Omnichannel Social Media Strategist and Copywriter. You receive \
real research data (trends, competitors, platform best practices) alongside brand DNA.

Your job is TWO things:
1. SYNTHESIZE the research into a clear strategy (best format, angle, hook, visual direction)
2. WRITE the actual post copy based on that strategy

### Strategy (brief, before the post):
- Recommended format and why (backed by trends research)
- Content angle/hook (informed by competitor gaps)
- Visual direction (aligned with platform best practices)

### Post Copy Guidelines:
- Blend brandTone (permanent identity) with postTone (this post's mood)
- LinkedIn = thought leadership, structured body | Instagram = visual storytelling, punchy
- 1300-character limit
- 3-5 relevant lowercase hashtags
- Line breaks for readability
- CTA at the bottom

### Output Format:
STRATEGY:
[brief strategy notes]
---
[ready-to-publish post text]

### Critical Rules:
- Strategy must reference specific findings from the research data
- If user provides complete post text and asks to keep it, only correct grammar + apply brandTone\
"""

USER_PROMPT_TEMPLATE = """\
## User Request
Topic: {topic}
Platform: {platform}
Post Type: {post_type}
Post Tone: {post_tone}

## Business DNA
{brand_dna}

Brand Tone: {brand_tone}

## Research — Trending Formats
{research_trends}

## Research — Competitor Analysis
{research_competitors}

## Research — Platform Best Practices
{research_platform}

Synthesize the research into a content strategy, then generate the post copy.\
"""


def build_user_prompt(state: dict) -> str:
    import json

    brand_dna = state.get("brand_dna", {})
    identity = state.get("identity", {})
    brand_tone = brand_dna.get("tone", {}).get("voice", "")

    return USER_PROMPT_TEMPLATE.format(
        topic=state.get("prompt", ""),
        platform=", ".join(state.get("platforms", [])),
        post_type=state.get("post_type", ""),
        post_tone=state.get("post_tone", ""),
        brand_dna=json.dumps(brand_dna),
        brand_tone=brand_tone,
        research_trends=json.dumps(state.get("research_trends", {})),
        research_competitors=json.dumps(state.get("research_competitors", {})),
        research_platform=json.dumps(state.get("research_platform", {})),
    )
