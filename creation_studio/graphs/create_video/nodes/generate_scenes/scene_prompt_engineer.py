"""Pure function — builds the Veo text prompt for a single video scene."""


def _hex_to_color_name(hex_color: str) -> str:
    """Convert a hex color to a descriptive name so Veo never sees raw hex codes."""
    if not hex_color or not hex_color.startswith("#") or len(hex_color) < 4:
        return "neutral tone"
    try:
        if len(hex_color) == 4:
            r = int(hex_color[1] * 2, 16)
            g = int(hex_color[2] * 2, 16)
            b = int(hex_color[3] * 2, 16)
        else:
            r = int(hex_color[1:3], 16)
            g = int(hex_color[3:5], 16)
            b = int(hex_color[5:7], 16)
    except ValueError:
        return "neutral tone"

    bright = (r + g + b) / 3
    diff = max(r, g, b) - min(r, g, b)

    if diff < 15:
        if bright > 240:
            return "white"
        if bright > 200:
            return "off-white"
        if bright > 150:
            return "light gray"
        if bright > 80:
            return "gray"
        if bright > 30:
            return "charcoal"
        return "black"

    mx = max(r, g, b)
    if mx == r:
        hue = "gold" if (g > b + 40 and r > 180 and g > 140) else \
              "warm amber" if g > b + 40 else \
              "orange" if (g > b and r > 180) else \
              "brown" if g > b else \
              "red" if r > 180 else "dark red"
    elif mx == g:
        hue = "teal" if b > r + 20 else "olive" if r > b else "green"
    else:
        hue = "purple" if r > g + 40 else "violet" if r > g else "blue"

    lightness = "very light" if bright > 210 else \
                "light" if bright > 170 else \
                "medium" if bright > 110 else \
                "dark" if bright > 50 else "very dark"

    return f"{lightness} {hue}"


def build_scene_prompt(
    scene: dict,
    brand_dna: dict,
    aspect_ratio: str,
    scene_duration: int,
    company: str = "",
    template_context: str = "",
) -> str:
    """Return a Veo-ready text prompt for a single video scene."""
    palette = brand_dna.get("color_palette", {})
    primary_name = _hex_to_color_name(palette.get("primary", ""))
    accent_name = _hex_to_color_name(palette.get("accent", ""))

    visual_prompt = scene.get("visual_prompt", "")
    camera = scene.get("camera_movement", "smooth cinematic movement")
    mood = scene.get("mood", "professional")
    brand_label = f"branded for {company}" if company else "premium look"

    style_ref = ""
    if template_context and len(template_context) > 50:
        style_ref = (
            "Visual style reference: "
            + template_context[:300].replace("\n", " ").strip()
            + " "
        )

    return (
        f"{visual_prompt} "
        f"Color palette: {primary_name} with {accent_name} accents. "
        f"Camera: {camera}. "
        f"Mood: {mood}. "
        f"Style: high-quality, polished, {brand_label}. "
        f"{style_ref}"
        f"No text, no watermarks, no UI elements. Purely visual cinematic footage. "
        f"Aspect ratio: {aspect_ratio}. Duration: {scene_duration} seconds."
    )
