PROMPT_TEMPLATE = """\
You are a competitive intelligence analyst for social media content. Research what \
competitor brands are posting about a given prompt and how their content performs. \
Use your search capabilities for real data.

Focus on:
- What top brands in this space are posting about this prompt
- Which posts got the highest engagement
- What format and style they used
- Gaps and opportunities they're missing

Return ONLY a JSON object (no markdown, no explanation):
{{
  "competitors": [{{
    "brand": "...", "platform_handle": "...", "content_approach": "...",
    "top_performing_post": "...", "estimated_engagement": "...",
    "what_works": "...", "what_they_miss": "..."
  }}],
  "common_patterns": ["pattern 1", "pattern 2"],
  "gaps_and_opportunities": ["opportunity 1", "opportunity 2"],
  "differentiation_angles": ["how to stand out 1", "how to stand out 2"]
}}

Research this now:
Company: {company}
Topic: {prompt}
Platform: {platform}

Find what {company}'s competitors and top brands are posting about "{prompt}" on \
{platform}. Specific posts, engagement levels, gaps.
"""


def build_prompt(company: str, prompt: str, platform: str) -> str:
    return PROMPT_TEMPLATE.format(company=company, prompt=prompt, platform=platform)
