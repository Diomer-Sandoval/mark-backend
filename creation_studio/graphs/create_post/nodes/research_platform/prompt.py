PROMPT_TEMPLATE = """\
You are a platform algorithm and engagement specialist. Research the current best \
practices, algorithm preferences, and engagement benchmarks for a specific social \
media platform. Use your search capabilities for real data.

Focus on:
- Current algorithm priorities (what gets boosted/suppressed)
- Optimal posting times, frequency, and formats
- Engagement rate benchmarks for this niche
- Hashtag/keyword strategy
- Platform-specific metrics that matter most

Return ONLY a JSON object (no markdown, no explanation):
{{
  "algorithm_insights": {{
    "boosted": ["what gets promoted"],
    "suppressed": ["what gets buried"],
    "recent_changes": "any recent updates"
  }},
  "optimal_posting": {{
    "best_times": "...", "frequency": "...", "best_formats": ["format 1", "format 2"]
  }},
  "engagement_benchmarks": {{
    "average_engagement_rate": "...", "good_engagement_rate": "...",
    "top_metric_to_optimize": "..."
  }},
  "hashtag_strategy": {{
    "recommended_count": "...", "mix": "...", "trending_tags": ["#tag1", "#tag2"]
  }},
  "platform_kpis": {{
    "primary": "...", "secondary": ["..."], "calculation": "..."
  }},
  "pro_tips": ["tip 1", "tip 2", "tip 3"]
}}

Research this now:
Platform: {platform}
Niche/Topic: {prompt}

Find the latest {platform} algorithm updates, engagement benchmarks for "{prompt}", \
optimal posting strategies, and which metrics matter most.
"""


def build_prompt(prompt: str, platform: str) -> str:
    return PROMPT_TEMPLATE.format(prompt=prompt, platform=platform)
