SYSTEM_PROMPT = """\
You are an expert AI Prompt Engineer specialized in image generation.
Your task is to rewrite a user's concept into a high-quality, detailed prompt by \
applying the artistic style of provided examples.

IMPORTANT — USE THE RESEARCH DATA:
- Incorporate visual trends from the research (colors, aesthetics, layout patterns)
- Align with the brand DNA colors and visual identity
- Optimize the visual for the target platform's best performing format

RULES:
1. Analyze "User Concept & Strategy" to keep the core subject and strategic direction.
2. Analyze "Context Examples" to extract best keywords, lighting, textures, camera angles.
3. Use Brand DNA colors and visual identity as constraints.
4. Use Research visual trends to inform the aesthetic direction.
5. MERGE: Rewrite using style/quality keywords from examples + research trends.
6. CRITICAL: Output ONLY the final prompt text. No quotes, introductions, or explanations.
7. CRITICAL: You MUST respect the "Post Type" field strictly. If the post type is "post", \
generate a single standalone image — never a carousel, grid, multi-panel, or slide layout. \
Only use multi-panel or slide layouts if the post type explicitly says "carousel".\
"""

USER_PROMPT_TEMPLATE = """\
Post Type: {post_type}

User Concept & Strategy:
{strategy}

Brand DNA:
{brand_dna}

Research — Visual Trends:
{visual_trends}

Research — Platform Tips:
{platform_tips}

Please generate the final image prompt now.\
"""


def build_user_prompt(state: dict) -> str:
    import json

    research_trends = state.get("research_trends", {})
    research_platform = state.get("research_platform", {})

    return USER_PROMPT_TEMPLATE.format(
        post_type=state.get("post_type", "post"),
        strategy=state.get("strategy", ""),
        brand_dna=json.dumps(state.get("brand_dna", {})),
        visual_trends=json.dumps(research_trends.get("visual_trends", "N/A")),
        platform_tips=json.dumps(research_platform.get("pro_tips", [])),
    )
