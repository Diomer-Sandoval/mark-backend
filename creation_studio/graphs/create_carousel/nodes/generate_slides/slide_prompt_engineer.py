"""Pure function — builds the text prompt sent to Gemini image generation per slide."""

_PLATFORM_SAFE_ZONES = {
    "instagram": 150,
    "linkedin": 120,
}

_DEFAULT_SAFE_ZONE = 150


def build_slide_prompt(
    slide: dict,
    brand_dna: dict,
    platform: str,
    visual_theme: str,
    template_context: str = "",
    qc_feedback: str = "",
) -> str:
    """Return a text prompt for Gemini image generation for a single carousel slide.

    Parameters
    ----------
    slide : dict  — {index, headline, body, visual_description}
    brand_dna : dict — {color_palette, typography, tone}
    platform : str — e.g. "instagram"
    visual_theme : str — overall art direction from carousel strategy
    template_context : str — optional template hint from retriever
    qc_feedback : str — issues from a previous QC attempt (empty on first try)
    """
    palette = brand_dna.get("color_palette", {})
    typography = brand_dna.get("typography", {})
    heading_font = typography.get("heading_font", "bold sans-serif")
    body_font = typography.get("body_font", "sans-serif")

    primary_name = "primary brand color"
    secondary_name = "secondary brand color"
    accent_name = "accent color"

    safe_zone = _PLATFORM_SAFE_ZONES.get(platform.lower(), _DEFAULT_SAFE_ZONE)

    headline = slide.get("headline", "")
    body_text = slide.get("body", "")
    visual_desc = slide.get("visual_description", "")
    slide_index = slide.get("index", 0)

    feedback_section = ""
    if qc_feedback:
        feedback_section = f"\n\n### QC FEEDBACK FROM PREVIOUS ATTEMPT — FIX THESE:\n{qc_feedback}"

    template_section = ""
    if template_context:
        template_section = f"\n\n### Template Reference:\n{template_context}"

    return f"""\
Create a 1080×1080 pixel social media carousel slide (slide {slide_index + 1}).

### Overall Visual Theme
{visual_theme}

### This Slide Content
Headline (render WORD-FOR-WORD): "{headline}"
Body copy (render WORD-FOR-WORD): "{body_text}"
Visual direction: {visual_desc}

### Brand Design System
- Background: {primary_name}
- Accent elements: {secondary_name} and {accent_name}
- Headline font: {heading_font} — large, high-contrast, clearly readable
- Body font: {body_font} — clean, smaller size
- Do NOT show any hex color codes (#XXXXXX) anywhere in the image

### Layout Rules
- Safe zone: keep all text and logo within {safe_zone}px margins on all sides
- Logo placement: top-left corner, within a 120×120px zone
- The provided logo image MUST appear in the top-left corner at approximately 80×80px
- Text must not overlap with the logo
- Slide dimensions: exactly 1080×1080px{template_section}{feedback_section}

Render the headline and body copy exactly as given above. Ensure the text is crisp and legible.\
"""
