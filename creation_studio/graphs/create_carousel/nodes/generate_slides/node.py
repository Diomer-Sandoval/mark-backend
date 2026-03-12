import random
import string
import concurrent.futures

from creation_studio.graphs.utils.gemini_utils import generate_image_with_logo
from creation_studio.graphs.utils.cloudinary_utils import upload_image
from creation_studio.graphs.create_carousel.state import CarouselPipelineState
from .slide_prompt_engineer import build_slide_prompt
from .slide_qc_validator import validate_slide

MAX_RETRIES = 3


def _make_uuid(length: int = 17) -> str:
    chars = string.ascii_letters + string.digits
    return "".join(random.choices(chars, k=length))


def _process_single_slide(slide, brand_dna, platform, visual_theme, template_context, logo_base64, logo_mime_type, creation_uuid):
    """Helper for parallel processing of a single slide."""
    expected_headline = slide.get("headline", "")
    qc_feedback = ""
    image_url = ""
    qc_passed = False
    attempts = 0
    last_error = ""

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
            image_b64 = None
            continue

        if not image_b64:
            last_error = "Image generation returned no data"
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
                image_url = ""
            break
        else:
            qc_feedback = "\n".join(issues)

    slide_result = {
        "index": slide.get("index", 0),
        "headline": expected_headline,
        "image_url": image_url,
        "qc_passed": qc_passed,
        "qc_attempts": attempts,
    }
    if not image_url and last_error:
        slide_result["error"] = last_error
    
    return slide_result


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

    # Process slides in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(
                _process_single_slide,
                slide, brand_dna, platform, visual_theme, 
                template_context, logo_base64, logo_mime_type, creation_uuid
            )
            for slide in slides_spec
        ]
        for future in concurrent.futures.as_completed(futures):
            try:
                completed_slides.append(future.result())
            except Exception as e:
                print(f"[carousel] Error in parallel slide processing: {e}")

    # Re-sort to maintain order
    completed_slides.sort(key=lambda x: x.get("index", 0))

    return {"completed_slides": completed_slides}
