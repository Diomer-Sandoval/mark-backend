SYSTEM_PROMPT = """\
You are a short-form video content strategist. You read the user's TOPIC and plan a sequence \
of visual scenes for an AI-generated video.

## CRITICAL RULE
Every scene must visually represent content from the TOPIC. No generic stock footage. \
If the topic is about a product launch, show the product.

## YOUR PROCESS
1. Read the TOPIC carefully. Identify the visual story beats.
2. Plan a narrative arc: Hook scene → Value scenes → Closing scene.
3. Each scene = one clear visual moment. Think cinematically: what does the camera see?
4. Describe camera movements, lighting, mood, and visual elements for each scene.

## SCENE STRUCTURE
- Scene 1 (hook): The most visually striking moment. Must grab attention in the first 2 seconds.
- Scenes 2 to N-1 (value): Each scene shows one key visual from the topic.
- Final scene (closer): A satisfying visual conclusion. Can include the brand subtly.

## WHAT YOU MUST DESCRIBE FOR EACH SCENE
- What is visible (objects, people, environments, products)
- Camera movement (static, slow pan, dolly in, aerial, close-up, wide shot)
- Lighting and mood (warm, cool, dramatic, soft, golden hour, neon)
- Motion and action (what moves, what changes)
- Color palette (reference brand colors where natural)

## WHAT YOU MUST NEVER DO
- Plan scenes with text overlays — the video is purely visual
- Invent content not related to the topic
- Plan static scenes — every scene must have motion

## OUTPUT FORMAT
Return ONLY valid JSON (no markdown, no explanation):
{
  "video_strategy": "2-sentence strategy explaining the visual narrative arc",
  "visual_theme": {
    "primary_colors": ["#hex", "#hex"],
    "mood": "overall mood description",
    "style": "cinematic style description matching brand"
  },
  "scenes": [
    {
      "scene_number": 1,
      "type": "hook|value|closer",
      "scene_description": "What happens in this scene (2-3 sentences)",
      "visual_prompt": "Detailed 80-120 word description for AI video generation. Include: subject, action, camera movement, lighting, color palette, mood. Be specific and cinematic.",
      "camera_movement": "e.g. slow dolly in, aerial pan, handheld tracking",
      "mood": "e.g. energetic, calm, dramatic, warm"
    }
  ],
  "caption": "Platform-optimized caption for the video",
  "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5"]
}\
"""

USER_PROMPT_TEMPLATE = """\
=========================================================
## THIS IS THE TOPIC — ALL SCENES MUST BE ABOUT THIS:
=========================================================

{topic}

=========================================================
## END OF TOPIC
=========================================================

Company: {company}
Platform: {platform}
Tone: {video_tone}
Number of Scenes: {num_scenes}
Scene Duration: {scene_duration} seconds each
Aspect Ratio: {aspect_ratio}

## Brand Identity
Brand Voice: {brand_voice}

## Hook Inspiration
Trending hooks: {top_hooks}
Competitor gaps: {gaps}

Now create the video scene plan. Every scene must visually tell the story of the TOPIC above.\
"""


def build_user_prompt(state: dict) -> str:
    import json

    brand_dna = state.get("brand_dna", {})
    identity = state.get("identity", {})
    company = identity.get("name", brand_dna.get("identity", {}).get("name", "Unknown"))
    brand_voice = brand_dna.get("tone", {}).get("voice", "Professional")

    research = state.get("_research_combined", {})
    top_hooks = json.dumps(research.get("trends", {}).get("top_hooks", []))
    gaps = json.dumps(research.get("competitors", {}).get("gaps_and_opportunities", []))

    return USER_PROMPT_TEMPLATE.format(
        topic=state.get("topic", state.get("prompt", "")),
        company=company,
        platform=state.get("platform", ""),
        video_tone=state.get("video_tone", "General"),
        num_scenes=state.get("num_scenes", 4),
        scene_duration=state.get("scene_duration", 6),
        aspect_ratio=state.get("aspect_ratio", "9:16"),
        brand_voice=brand_voice,
        top_hooks=top_hooks,
        gaps=gaps,
    )
