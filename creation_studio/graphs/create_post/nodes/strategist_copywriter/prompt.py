SYSTEM_PROMPT = """\
You are a Senior Omnichannel Social Media Strategist and Copywriter. You receive \
real research data (trends, competitors, platform best practices) alongside brand DNA.

Your job is TWO things:
1. SYNTHESIZE the research into a clear strategy (best format, angle, hook, visual direction)
2. WRITE the actual post copy based on that strategy

### Strategy (brief, before the post):
- Recommended format and why (backed by research, or existing context if editing)
- Content angle/hook (informed by competitors or user feedback)
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
- Strategy should reference specific findings from research data if provided.
- If research is not provided (common during quick edits), base strategy on the existing copy and user feedback.
- If user provides complete post text and asks to keep it, only correct grammar + apply brandTone\
"""

USER_PROMPT_TEMPLATE = """\
## User Request
Prompt: {prompt}
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

Synthesize the research into a content strategy, then generate the post copy.{feedback_section}\
"""


def build_user_prompt(state: dict) -> str:
    import json

    brand_dna = state.get("brand_dna", {})
    identity = state.get("identity", {})
    brand_tone = brand_dna.get("tone", {}).get("voice", "")
    current_copy = state.get("current_copy", "")
    copy_feedback = state.get("copy_feedback", "")

    feedback_section = ""
    if current_copy:
        feedback_section += f"\n\n## Current Copy\n{current_copy}"
    if copy_feedback:
        feedback_section += f"\n\n## Copy Feedback\n{copy_feedback}"

    return USER_PROMPT_TEMPLATE.format(
        prompt=state.get("prompt", ""),
        platform=", ".join(state.get("platforms", [])),
        post_type=state.get("post_type", ""),
        post_tone=state.get("post_tone", ""),
        brand_dna=json.dumps(brand_dna),
        brand_tone=brand_tone,
        research_trends=json.dumps(state.get("research_trends", {})),
        research_competitors=json.dumps(state.get("research_competitors", {})),
        research_platform=json.dumps(state.get("research_platform", {})),
        feedback_section=feedback_section,
    )
