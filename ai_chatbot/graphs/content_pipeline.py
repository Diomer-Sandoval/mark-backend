"""
MARK Content Generation Pipeline — Python port of the n8n workflow.

Architecture (mirrors the n8n R&D pipeline exactly):

  User Input (post idea, platform, tone, brand DNA)
       │
       ├─── [PARALLEL RESEARCH] ────────────────────────────────────┐
       │         ├── Trends Researcher    (what's trending now)      │
       │         ├── Competitor Analyst   (what is competition doing) │
       │         └── Platform Specialist  (platform-specific tips)   │
       └─────────────────────────────────────────────────────────┘
                             │  (merge all research)
                             ▼
                   Strategist + Copywriter
                   (GPT-4.1-mini with brand DNA + research →
                    strategy, hooks, copy variations, hashtags)
                             │
                             ▼
                   Visual Prompt Engineer
                   (rewrites copy into optimised image gen prompt)
                             │
                             ▼
                   Structured Output
                   {strategy, copies[], image_prompt, hashtags, cta}
"""

import json
import logging
import concurrent.futures
from dataclasses import dataclass, field
from typing import Optional
from openai import OpenAI

logger = logging.getLogger(__name__)

# ─── OpenAI client (picked up from OPENAI_API_KEY env var) ─────────────────
_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI()
    return _client


# ─── Dataclasses ────────────────────────────────────────────────────────────

@dataclass
class ContentRequest:
    """Input to the content generation pipeline."""
    post_idea: str
    platform: str                      # instagram | facebook | linkedin | tiktok | twitter
    tone: str = "professional"         # professional | casual | humorous | inspirational | urgent
    brand_name: str = ""
    brand_dna: Optional[dict] = None   # Full BrandDNA JSON if available
    target_audience: str = ""
    industry: str = ""
    additional_context: str = ""
    generate_image: bool = False       # If True, call DALL-E 3 after prompt engineering


@dataclass
class ResearchOutput:
    """Results from the parallel research phase."""
    trends: str = ""
    competitors: str = ""
    platform_tips: str = ""
    errors: list = field(default_factory=list)


@dataclass
class ContentOutput:
    """Final output of the content pipeline."""
    success: bool = True
    error: str = ""

    # Strategy layer
    strategy: str = ""
    hook_options: list = field(default_factory=list)  # 3 hook variations

    # Copy layer
    primary_copy: str = ""
    copy_variations: list = field(default_factory=list)  # Shorter/longer alternatives

    # Visual layer
    image_prompt: str = ""

    # Metadata
    hashtags: list = field(default_factory=list)
    cta: str = ""
    platform: str = ""
    tone: str = ""

    # Generated image (populated when generate_image=True)
    image_url: str = ""
    image_revised_prompt: str = ""

    # Research used
    research: Optional[ResearchOutput] = None


# ─── PROMPTS ────────────────────────────────────────────────────────────────

_TRENDS_PROMPT = """You are a Social Media Trends Researcher specialising in {platform} content.

Research and report on what is currently trending for brands in the {industry} industry on {platform}.

Cover:
1. Content formats performing best right now (reels, carousels, polls, etc.)
2. Topics and themes getting the most engagement
3. Hashtag strategies currently working
4. Tone and style that resonates with audiences
5. Any algorithm changes that affect reach

Post idea context: {post_idea}
Target audience: {target_audience}

Be specific, data-driven, and actionable. Keep your answer under 400 words."""

_COMPETITOR_PROMPT = """You are a Competitive Intelligence Analyst for digital marketing.

Analyse the competitive content landscape for brands in the {industry} industry targeting {target_audience} on {platform}.

Provide:
1. What high-performing competitor content looks like (structure, length, format)
2. Content gaps — what competitors are NOT doing well that we can exploit
3. Messaging angles competitors use (and any that feel overdone/saturated)
4. Visual and aesthetic themes dominating the space
5. Engagement tactics competitors rely on

Post idea context: {post_idea}

Be specific and actionable. Keep your answer under 400 words."""

_PLATFORM_PROMPT = """You are a Platform Algorithm & Best Practices Expert for {platform}.

Give a concise, tactical brief for maximising reach and engagement on {platform} for this content:

Post idea: {post_idea}
Tone: {tone}
Target audience: {target_audience}

Include:
1. Optimal post length / character count
2. Hashtag count and placement strategy
3. Best posting time (general guidance)
4. Caption structure that works (hook → body → CTA)
5. Media specs (image ratio, video length if applicable)
6. {platform}-specific algorithm tips for 2024/2025
7. Common mistakes to avoid

Keep your answer under 350 words. Be direct and tactical."""

_STRATEGIST_PROMPT = """You are a world-class Social Media Strategist and Copywriter.
You apply Cialdini's 7 principles of persuasion and proven direct-response copywriting frameworks.

## Brand Context
Brand: {brand_name}
Industry: {industry}
Target Audience: {target_audience}
Brand Tone: {tone}
Brand DNA: {brand_dna_text}

## Platform
{platform}

## Post Idea
{post_idea}

## Research Findings
### What's Trending
{trends}

### Competitive Landscape
{competitors}

### Platform Best Practices
{platform_tips}

---

Create a complete content brief with the following JSON structure (respond ONLY with valid JSON):

{{
  "strategy": "2-3 sentence strategic rationale for this content",
  "hook_options": [
    "Hook option 1 — pattern interrupt / curiosity",
    "Hook option 2 — bold claim / contrarian",
    "Hook option 3 — direct problem agitation"
  ],
  "primary_copy": "Full post copy, ready to publish. Includes hook, body, and CTA. Optimised for {platform}.",
  "copy_variations": [
    "Shorter version (30% less words, same hook)",
    "A/B test variation with different angle"
  ],
  "hashtags": ["#hashtag1", "#hashtag2", "#hashtag3", "#hashtag4", "#hashtag5"],
  "cta": "Clear call-to-action sentence",
  "visual_direction": "Brief description of ideal image/video concept to accompany this post"
}}

Rules:
- Primary copy must be platform-appropriate length
- Use the research to make the copy feel timely and relevant
- Apply at least one Cialdini principle (social proof, scarcity, authority, liking, reciprocity, commitment, unity)
- No corporate jargon — write like a human, for humans"""

_PROMPT_ENGINEER_PROMPT = """You are a Visual Prompt Engineer specialising in AI-generated marketing images.

Convert this social media content brief into an optimised image generation prompt for a marketing visual.

## Content Brief
Platform: {platform}
Brand: {brand_name}
Industry: {industry}
Post copy: {primary_copy}
Visual direction: {visual_direction}
Brand colors: {brand_colors}
Brand tone: {tone}

## Task
Write an image generation prompt (for DALL-E 3 or similar) that would produce a premium, on-brand marketing visual.

Rules:
- Be highly specific about composition, lighting, style, color palette
- Include platform format (e.g., "square 1:1 composition for Instagram")
- Avoid text in the image unless explicitly needed
- Specify photographic style OR illustration style NOT both
- Include mood and atmosphere
- Mention brand color accent if colors are provided

Respond with ONLY the image prompt text, no extra explanation or JSON."""


# ─── RESEARCH WORKERS ────────────────────────────────────────────────────────

def _run_research(prompt: str, system_role: str = "You are a helpful marketing researcher.") -> str:
    """Run a single research LLM call."""
    try:
        client = _get_client()
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": system_role},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=600,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error("Research LLM error: %s", e)
        return f"[Research unavailable: {str(e)[:100]}]"


def _research_trends(req: ContentRequest) -> str:
    prompt = _TRENDS_PROMPT.format(
        platform=req.platform,
        industry=req.industry or "general",
        post_idea=req.post_idea,
        target_audience=req.target_audience or "general audience",
    )
    return _run_research(prompt, "You are a social media trends expert.")


def _research_competitors(req: ContentRequest) -> str:
    prompt = _COMPETITOR_PROMPT.format(
        platform=req.platform,
        industry=req.industry or "general",
        post_idea=req.post_idea,
        target_audience=req.target_audience or "general audience",
    )
    return _run_research(prompt, "You are a competitive intelligence analyst.")


def _research_platform(req: ContentRequest) -> str:
    prompt = _PLATFORM_PROMPT.format(
        platform=req.platform,
        post_idea=req.post_idea,
        tone=req.tone,
        target_audience=req.target_audience or "general audience",
    )
    return _run_research(prompt, "You are a platform algorithm specialist.")


# ─── PARALLEL RESEARCH PHASE ─────────────────────────────────────────────────

def run_parallel_research(req: ContentRequest) -> ResearchOutput:
    """
    Run all three research tasks in parallel using a thread pool.
    Mirrors the n8n workflow's parallel research phase.
    """
    research = ResearchOutput()

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        future_trends = executor.submit(_research_trends, req)
        future_competitors = executor.submit(_research_competitors, req)
        future_platform = executor.submit(_research_platform, req)

        try:
            research.trends = future_trends.result(timeout=30)
        except Exception as e:
            research.errors.append(f"trends: {e}")
            research.trends = "Trend research unavailable."

        try:
            research.competitors = future_competitors.result(timeout=30)
        except Exception as e:
            research.errors.append(f"competitors: {e}")
            research.competitors = "Competitor research unavailable."

        try:
            research.platform_tips = future_platform.result(timeout=30)
        except Exception as e:
            research.errors.append(f"platform: {e}")
            research.platform_tips = "Platform tips unavailable."

    return research


# ─── STRATEGIST + COPYWRITER ─────────────────────────────────────────────────

def run_strategist(req: ContentRequest, research: ResearchOutput) -> dict:
    """
    Strategist + Copywriter node (mirrors n8n GPT-4.1-mini strategist).
    Takes merged research and produces the full content brief as JSON.
    """
    # Format brand DNA for prompt
    brand_dna_text = "No specific brand DNA provided."
    brand_colors = ""
    if req.brand_dna:
        dna = req.brand_dna
        brand_dna_text = f"""
- Voice/Tone: {dna.get('voice_tone', req.tone)}
- Keywords: {dna.get('keywords', '')}
- Description: {dna.get('description', '')}
- Archetype: {dna.get('archetype', '')}
- Target Audience: {dna.get('target_audience', req.target_audience)}
        """.strip()
        primary = dna.get('primary_color', '')
        secondary = dna.get('secondary_color', '')
        accent = dna.get('accent_color', '')
        brand_colors = ", ".join(c for c in [primary, secondary, accent] if c)

    prompt = _STRATEGIST_PROMPT.format(
        brand_name=req.brand_name or "the brand",
        industry=req.industry or "general",
        target_audience=req.target_audience or "general audience",
        tone=req.tone,
        brand_dna_text=brand_dna_text,
        platform=req.platform,
        post_idea=req.post_idea,
        trends=research.trends,
        competitors=research.competitors,
        platform_tips=research.platform_tips,
    )

    try:
        client = _get_client()
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "You are a world-class marketing strategist and copywriter. Always respond with valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=1500,
            response_format={"type": "json_object"},  # Force JSON mode
        )
        raw = response.choices[0].message.content.strip()
        result = json.loads(raw)
        result["_brand_colors"] = brand_colors  # Pass through for prompt engineer
        return result
    except json.JSONDecodeError as e:
        logger.error("Strategist JSON parse error: %s", e)
        return {"error": f"JSON parse error: {e}", "primary_copy": req.post_idea}
    except Exception as e:
        logger.error("Strategist error: %s", e)
        return {"error": str(e), "primary_copy": req.post_idea}


# ─── VISUAL PROMPT ENGINEER ───────────────────────────────────────────────────

def run_prompt_engineer(req: ContentRequest, strategy_output: dict) -> str:
    """
    Prompt Engineer node (mirrors n8n prompt engineer step).
    Converts the content brief into an optimised image generation prompt.
    """
    prompt = _PROMPT_ENGINEER_PROMPT.format(
        platform=req.platform,
        brand_name=req.brand_name or "the brand",
        industry=req.industry or "general",
        primary_copy=strategy_output.get("primary_copy", req.post_idea)[:300],
        visual_direction=strategy_output.get("visual_direction", "Modern, clean marketing visual"),
        brand_colors=strategy_output.get("_brand_colors", ""),
        tone=req.tone,
    )

    try:
        client = _get_client()
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "You are an expert AI image prompt engineer for marketing visuals."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.6,
            max_tokens=400,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error("Prompt engineer error: %s", e)
        return f"Professional marketing visual for {req.platform}, clean design, brand colors, high quality photography"


# ─── MAIN PIPELINE ENTRY POINT ────────────────────────────────────────────────

def generate_marketing_content(req: ContentRequest) -> ContentOutput:
    """
    Full content generation pipeline — mirrors the n8n R&D workflow entirely.

    Steps:
      1. Parallel research (trends + competitors + platform) — ~15-20s
      2. Strategist + Copywriter — ~10s
      3. Prompt Engineer — ~5s

    Total: ~20-30s (parallel phases overlap the sequential ones)
    """
    logger.info("Content pipeline started: platform=%s idea='%s...'", req.platform, req.post_idea[:50])

    # Phase 1: Parallel research
    try:
        research = run_parallel_research(req)
        logger.info("Research complete (errors: %s)", research.errors)
    except Exception as e:
        logger.error("Research phase failed: %s", e)
        research = ResearchOutput(errors=[str(e)])

    # Phase 2: Strategist + Copywriter
    try:
        strategy = run_strategist(req, research)
        if "error" in strategy:
            logger.warning("Strategist returned error: %s", strategy["error"])
    except Exception as e:
        logger.error("Strategist phase failed: %s", e)
        return ContentOutput(
            success=False,
            error=f"Content strategy failed: {str(e)}",
            platform=req.platform,
            tone=req.tone,
        )

    # Phase 3: Visual Prompt Engineer
    try:
        image_prompt = run_prompt_engineer(req, strategy)
    except Exception as e:
        logger.warning("Prompt engineer failed (non-fatal): %s", e)
        image_prompt = ""

    # Phase 4 (optional): DALL-E 3 Image Generation
    image_url = ""
    image_revised_prompt = ""
    if req.generate_image and image_prompt:
        try:
            import os
            client = _get_client()
            img_response = client.images.generate(
                model=os.getenv("OPENAI_IMAGE_MODEL", "dall-e-3"),
                prompt=image_prompt,
                size="1024x1024",
                quality="standard",
                n=1,
            )
            image_url = img_response.data[0].url or ""
            image_revised_prompt = img_response.data[0].revised_prompt or ""
            logger.info("Image generated successfully for pipeline request")
        except Exception as e:
            logger.warning("Image generation failed (non-fatal): %s", e)

    # Assemble final output
    return ContentOutput(
        success=True,
        strategy=strategy.get("strategy", ""),
        hook_options=strategy.get("hook_options", []),
        primary_copy=strategy.get("primary_copy", ""),
        copy_variations=strategy.get("copy_variations", []),
        image_prompt=image_prompt,
        hashtags=strategy.get("hashtags", []),
        cta=strategy.get("cta", ""),
        platform=req.platform,
        tone=req.tone,
        image_url=image_url,
        image_revised_prompt=image_revised_prompt,
        research=research,
    )


# ─── CONVENIENCE FUNCTION ─────────────────────────────────────────────────────

def generate_from_dict(data: dict) -> dict:
    """
    Convenience wrapper that accepts a dict (from API request) and returns a dict.
    Easy to call from Django views.

    Expected input:
      {
        "post_idea": "...",
        "platform": "instagram",
        "tone": "casual",               # optional
        "brand_name": "Acme Co",        # optional
        "brand_dna": {...},             # optional — BrandDNA object from DB
        "target_audience": "...",       # optional
        "industry": "...",              # optional
        "additional_context": "..."     # optional
      }
    """
    req = ContentRequest(
        post_idea=data.get("post_idea", ""),
        platform=data.get("platform", "instagram"),
        tone=data.get("tone", "professional"),
        brand_name=data.get("brand_name", ""),
        brand_dna=data.get("brand_dna"),
        target_audience=data.get("target_audience", ""),
        industry=data.get("industry", ""),
        additional_context=data.get("additional_context", ""),
        generate_image=bool(data.get("generate_image", False)),
    )

    if not req.post_idea:
        return {"success": False, "error": "post_idea is required"}
    if not req.platform:
        return {"success": False, "error": "platform is required"}

    output = generate_marketing_content(req)

    return {
        "success": output.success,
        "error": output.error,
        "platform": output.platform,
        "tone": output.tone,
        "strategy": output.strategy,
        "hook_options": output.hook_options,
        "primary_copy": output.primary_copy,
        "copy_variations": output.copy_variations,
        "image_prompt": output.image_prompt,
        "image_url": output.image_url,
        "image_revised_prompt": output.image_revised_prompt,
        "hashtags": output.hashtags,
        "cta": output.cta,
        "research_errors": output.research.errors if output.research else [],
    }
