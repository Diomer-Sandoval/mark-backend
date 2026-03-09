import random
import string

from creation_studio.graphs.utils.gemini_utils import generate_image_with_logo
from creation_studio.graphs.utils.cloudinary_utils import upload_image
from creation_studio.graphs.create_carousel.state import CarouselPipelineState
from .slide_prompt_engineer import build_slide_prompt
from .slide_qc_validator import validate_slide

MAX_RETRIES = 3


def _make_uuid(length: int = 17) -> str:
    chars = string.ascii_letters + string.digits
    return "".join(random.choices(chars, k=length))


def generate_slides_node(state: CarouselPipelineState) -> dict:
    strategy = state.get("carousel_strategy", {})
    slides_spec = strategy.get("slides", [])
    visual_theme = strategy.get("visual_theme", "")
    brand_dna = state.get("brand_dna", {})
    platform = state.get("platform", (state.get("platforms") or ["instagram"])[0])
    template_context = state.get("template_context", "")
    logo_base64 = state.get("logo_base64", "")
    logo_mime_type = state.get("logo_mime_type", "image/png")
    creation_uuid = state.get("creation_uuid", _make_uuid())

    completed_slides = []

    for slide in slides_spec:
        expected_headline = slide.get("headline", "")
        qc_feedback = ""
        image_url = ""
        qc_passed = False
        attempts = 0

        last_error = ""
        image_b64 = None

        for attempt in range(1, MAX_RETRIES + 1):
            attempts = attempt
            prompt = build_slide_prompt(
                slide=slide,
                brand_dna=brand_dna,
                platform=platform,
                visual_theme=visual_theme,
                template_context=template_context,
                qc_feedback=qc_feedback,
            )

            try:
                image_b64 = generate_image_with_logo(
                    prompt=prompt,
                    logo_base64=logo_base64,
                    logo_mime_type=logo_mime_type,
                )
            except Exception as e:
                last_error = f"Image generation error: {e}"
                print(f"[carousel] slide {slide.get('index')} attempt {attempt}: {last_error}")
                image_b64 = None
                continue

            if not image_b64:
                last_error = "Image generation returned no data"
                print(f"[carousel] slide {slide.get('index')} attempt {attempt}: {last_error}")
                continue

            passed, issues = validate_slide(image_b64, expected_headline)
            qc_passed = passed

            if passed or attempt == MAX_RETRIES:
                generation_uuid = _make_uuid()
                folder = f"ia_generations/{creation_uuid}/carousel"
                try:
                    image_url = upload_image(image_b64, folder, generation_uuid)
                except Exception as e:
                    last_error = f"Cloudinary upload failed: {e}"
                    print(f"[carousel] slide {slide.get('index')}: {last_error}")
                    image_url = ""
                break
            else:
                qc_feedback = "\n".join(issues)

        slide_result = {
            "index": slide.get("index", len(completed_slides)),
            "headline": expected_headline,
            "image_url": image_url,
            "qc_passed": qc_passed,
            "qc_attempts": attempts,
        }
        if not image_url and last_error:
            slide_result["error"] = last_error

        completed_slides.append(slide_result)

    return {"completed_slides": completed_slides}
