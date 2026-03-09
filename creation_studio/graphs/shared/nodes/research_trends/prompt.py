PROMPT_TEMPLATE = """\
You are a social media trend analyst. Research what image-based content and styles \
are performing best RIGHT NOW for a given prompt and platform. Use your search \
capabilities for real current data.

Focus on:
- Top-performing content formats (carousel, infographic, reel, thread, single image, video)
- Viral examples and why they worked
- Current visual/design trends in this niche
- Hooks and angles that drive engagement

Return ONLY a JSON object (no markdown, no explanation):
{{
  "trending_formats": [{{"format": "...", "why_it_works": "...", "estimated_engagement": "...", "examples": ["..."]}}],
  "visual_trends": {{"aesthetics": "...", "color_trends": "...", "typography": "...", "layout_patterns": "..."}},
  "top_hooks": [{{"hook": "...", "why_effective": "...", "example": "..."}}],
  "content_angles": ["angle 1", "angle 2", "angle 3"],
  "top_pick": "Your #1 format recommendation and why"
}}

Research this now:
Company: {company}
Topic: {prompt}
Platform: {platform}

Find what's currently going viral and performing best on {platform} related to \
"{prompt}". Real examples, real engagement data, current design trends.
"""


def build_prompt(company: str, prompt: str, platform: str) -> str:
    return PROMPT_TEMPLATE.format(company=company, prompt=prompt, platform=platform)
