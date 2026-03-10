import json
import random
import string
from datetime import datetime, timezone

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .graphs.create_post import build_agent, build_copy_agent
from .graphs.edit_image import build_edit_image_agent
from .graphs.create_carousel.agent import build_carousel_agent
from .graphs.create_carousel.nodes.generate_slides.slide_prompt_engineer import build_slide_prompt
from .graphs.create_carousel.nodes.generate_slides.slide_qc_validator import validate_slide
from .graphs.create_carousel.nodes.generate_slides.node import MAX_RETRIES
from .graphs.create_video.agent import build_video_agent
from .graphs.utils.gemini_utils import generate_image_with_logo
from .graphs.utils.cloudinary_utils import upload_image
from .graphs.utils.firebase_utils import (
    create_creation,
    create_generation,
    update_creation,
)

agent = build_agent()
copy_agent = build_copy_agent()
edit_image_agent = build_edit_image_agent()
carousel_agent = build_carousel_agent()
video_agent = build_video_agent()

_ASPECT_RATIO_MAP = {
    "instagram reels": "9:16",
    "tiktok": "9:16",
    "youtube shorts": "9:16",
    "linkedin": "16:9",
    "facebook": "1:1",
    "youtube": "16:9",
}


def _resolve_logo(body: dict) -> tuple[str, str]:
    """Return (logo_base64, logo_mime_type) from request body.

    Priority: logo_base64 field → logo_url → identity.logo_url download → empty.
    """
    logo_b64 = body.get("logo_base64", "")
    logo_mime = body.get("logo_mime_type", "image/png")
    if logo_b64:
        return logo_b64, logo_mime

    logo_url = body.get("logo_url", "") or body.get("identity", {}).get("logo_url", "")
    if logo_url:
        try:
            import urllib.request
            import base64
            with urllib.request.urlopen(logo_url, timeout=10) as resp:
                raw = resp.read()
                content_type = resp.headers.get("Content-Type", "image/png").split(";")[0]
                return base64.b64encode(raw).decode(), content_type
        except Exception:
            pass

    return "", "image/png"


def _make_uuid(length: int = 17) -> str:
    chars = string.ascii_letters + string.digits
    return "".join(random.choices(chars, k=length))


@csrf_exempt
@require_POST
def generate_content(request):
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError as e:
        return JsonResponse({"error": f"Invalid JSON: {e}"}, status=400)
    now = datetime.now(timezone.utc).isoformat()
    creation_uuid = _make_uuid()

    platforms = body.get("platforms", ["instagram"])
    brand_dna = body.get("brand_dna", {})
    identity = body.get("identity", {})

    create_creation(
        creation_uuid,
        {
            "uuid": creation_uuid,
            "creation_at": now,
            "platforms": platforms,
            "post_type": body.get("post_type", ""),
            "post_tone": body.get("post_tone", ""),
            "identity": identity,
            "status": "pending",
            "update_at": now,
        },
    )

    initial_state = {
        "creation_uuid": creation_uuid,
        "prompt": body.get("prompt", ""),
        "platforms": platforms,
        "post_type": body.get("post_type", "post"),
        "post_tone": body.get("post_tone", "promotional"),
        "brand_dna": brand_dna,
        "identity": identity,
    }

    try:
        result = agent.invoke(initial_state)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)

    image_url = result.get("image_url", "")
    generation_uuid = result.get("generation_uuid", "")
    done_at = datetime.now(timezone.utc).isoformat()

    if generation_uuid:
        create_generation(
            creation_uuid,
            generation_uuid,
            {
                "uuid": generation_uuid,
                "creation_uuid": creation_uuid,
                "parent_uuid": creation_uuid,
                "img_url": image_url,
                "prompt": result.get("image_prompt", ""),
                "status": "done",
                "create_at": done_at,
            },
        )

    update_creation(creation_uuid, {"status": "active", "update_at": done_at})

    strategy_raw = result.get("strategy", "")
    if "---" in strategy_raw:
        strategy_part, copy_part = strategy_raw.split("---", 1)
        strategy_part = strategy_part.strip()
        copy_part = copy_part.strip()
    else:
        strategy_part = strategy_raw
        copy_part = ""

    return JsonResponse(
        {
            "uuid": creation_uuid,
            "copy": copy_part,
            "image_url": image_url,
        }
    )


@csrf_exempt
@require_POST
def regenerate_copy(request):
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError as e:
        return JsonResponse({"error": f"Invalid JSON: {e}"}, status=400)

    creation_uuid = body.get("creation_uuid", "")
    platforms = body.get("platforms", ["instagram"])
    brand_dna = {k: v for k, v in body.get("brand_dna", {}).items() if k != "typography"}
    identity = body.get("identity", {})
    now = datetime.now(timezone.utc).isoformat()

    update_creation(creation_uuid, {"status": "pending", "update_at": now})

    initial_state = {
        "creation_uuid": creation_uuid,
        "prompt": body.get("prompt", ""),
        "current_copy": body.get("current_copy", ""),
        "copy_feedback": body.get("copy_feedback", ""),
        "platforms": platforms,
        "post_type": body.get("post_type", "post"),
        "post_tone": body.get("post_tone", "promotional"),
        "brand_dna": brand_dna,
        "identity": identity,
    }

    try:
        result = copy_agent.invoke(initial_state)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)

    strategy_raw = result.get("strategy", "")
    if "---" in strategy_raw:
        _, copy_part = strategy_raw.split("---", 1)
        copy_part = copy_part.strip()
    else:
        copy_part = strategy_raw

    done_at = datetime.now(timezone.utc).isoformat()
    update_creation(creation_uuid, {"status": "active", "update_at": done_at})

    return JsonResponse({"uuid": creation_uuid, "copy": copy_part})


@csrf_exempt
@require_POST
def edit_image(request):
    body = json.loads(request.body)
    now = datetime.now(timezone.utc).isoformat()

    creation_uuid = body.get("creation_uuid", "")
    parent_uuid = body.get("uuid", "")
    prompt = body.get("prompt", "")
    img_url = body.get("img_url", "")

    update_creation(creation_uuid, {
        "status": "pending",
        "feedback": prompt,
        "update_at": now,
    })

    result = edit_image_agent.invoke({
        "creation_uuid": creation_uuid,
        "parent_uuid": parent_uuid,
        "prompt": prompt,
        "img_url": img_url,
    })

    result_url = result.get("result_url", "")
    generation_uuid = result.get("generation_uuid", "")
    done_at = datetime.now(timezone.utc).isoformat()

    if generation_uuid:
        create_generation(
            creation_uuid,
            generation_uuid,
            {
                "uuid": generation_uuid,
                "creation_uuid": creation_uuid,
                "parent_uuid": parent_uuid,
                "img_url": result_url,
                "prompt": prompt,
                "status": "done",
                "create_at": done_at,
            },
        )

    update_creation(creation_uuid, {"status": "active", "update_at": done_at})

    return JsonResponse({
        "status": "ok",
        "message": "Image edited successfully",
        "img_url": result_url,
    })


@csrf_exempt
@require_POST
def generate_carousel(request):
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError as e:
        return JsonResponse({"error": f"Invalid JSON: {e}"}, status=400)

    now = datetime.now(timezone.utc).isoformat()
    creation_uuid = _make_uuid()

    topic = body.get("topic", "")
    platform = body.get("platform", "instagram")
    post_tone = body.get("post_tone", "educational")
    num_slides = max(5, min(10, int(body.get("num_slides", 7))))
    brand_dna = body.get("brand_dna", {})
    identity = body.get("identity", {})

    logo_base64, logo_mime_type = _resolve_logo(body)

    create_creation(
        creation_uuid,
        {
            "uuid": creation_uuid,
            "creation_at": now,
            "type": "carousel",
            "platforms": [platform],
            "num_slides": num_slides,
            "post_tone": post_tone,
            "identity": identity,
            "status": "pending",
            "update_at": now,
        },
    )

    initial_state = {
        "creation_uuid": creation_uuid,
        "topic": topic,
        "prompt": topic,           # research nodes read "prompt"
        "platform": platform,
        "platforms": [platform],   # research nodes read "platforms"
        "post_tone": post_tone,
        "num_slides": num_slides,
        "brand_dna": brand_dna,
        "identity": identity,
        "logo_base64": logo_base64,
        "logo_mime_type": logo_mime_type,
    }

    try:
        result = carousel_agent.invoke(initial_state)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)

    completed_slides = result.get("completed_slides", [])
    done_at = datetime.now(timezone.utc).isoformat()

    for slide in completed_slides:
        generation_uuid = _make_uuid()
        create_generation(
            creation_uuid,
            generation_uuid,
            {
                "uuid": generation_uuid,
                "creation_uuid": creation_uuid,
                "slide_index": slide.get("index"),
                "img_url": slide.get("image_url", ""),
                "headline": slide.get("headline", ""),
                "qc_passed": slide.get("qc_passed", False),
                "qc_attempts": slide.get("qc_attempts", 1),
                "status": "done",
                "create_at": done_at,
            },
        )

    update_creation(creation_uuid, {"status": "active", "update_at": done_at})

    return JsonResponse(
        {
            "uuid": creation_uuid,
            "slides": completed_slides,
            "caption": result.get("caption", ""),
            "hashtags": result.get("hashtags", []),
        }
    )


@csrf_exempt
@require_POST
def edit_carousel_slide(request):
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError as e:
        return JsonResponse({"error": f"Invalid JSON: {e}"}, status=400)

    creation_uuid = body.get("creation_uuid", "")
    slide = body.get("slide", {})           # {index, headline, body, visual_description}
    visual_theme = body.get("visual_theme", "")
    brand_dna = body.get("brand_dna", {})
    platform = body.get("platform", "instagram")
    feedback = body.get("feedback", "")     # optional user feedback

    logo_base64, logo_mime_type = _resolve_logo(body)

    now = datetime.now(timezone.utc).isoformat()
    update_creation(creation_uuid, {"status": "pending", "update_at": now})

    slide_index = slide.get("index", 0)
    expected_headline = slide.get("headline", "")
    qc_feedback = feedback
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

            if image_url and creation_uuid:
                done_at = datetime.now(timezone.utc).isoformat()
                create_generation(
                    creation_uuid,
                    generation_uuid,
                    {
                        "uuid": generation_uuid,
                        "creation_uuid": creation_uuid,
                        "slide_index": slide_index,
                        "img_url": image_url,
                        "headline": expected_headline,
                        "qc_passed": qc_passed,
                        "qc_attempts": attempts,
                        "status": "done",
                        "create_at": done_at,
                    },
                )
            break
        else:
            qc_feedback = "\n".join(issues)

    done_at = datetime.now(timezone.utc).isoformat()
    update_creation(creation_uuid, {"status": "active", "update_at": done_at})

    slide_result = {
        "index": slide_index,
        "headline": expected_headline,
        "image_url": image_url,
        "qc_passed": qc_passed,
        "qc_attempts": attempts,
    }
    if not image_url and last_error:
        slide_result["error"] = last_error

    return JsonResponse({"uuid": creation_uuid, "slide": slide_result})


@csrf_exempt
@require_POST
def generate_video(request):
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError as e:
        return JsonResponse({"error": f"Invalid JSON: {e}"}, status=400)

    now = datetime.now(timezone.utc).isoformat()
    creation_uuid = _make_uuid()

    topic = body.get("topic", "")
    platform = body.get("platform", "Instagram Reels")
    video_tone = body.get("video_tone", "General")
    num_scenes = max(3, min(6, int(body.get("num_scenes", 4))))
    scene_duration = int(body.get("scene_duration", 6))
    if scene_duration not in (5, 6, 8):
        scene_duration = 6
    brand_dna = body.get("brand_dna", {})
    identity = body.get("identity", {})
    aspect_ratio = _ASPECT_RATIO_MAP.get(platform.lower(), "9:16")

    logo_base64, logo_mime_type = _resolve_logo(body)

    create_creation(
        creation_uuid,
        {
            "uuid": creation_uuid,
            "creation_at": now,
            "type": "video",
            "platforms": [platform],
            "num_scenes": num_scenes,
            "scene_duration": scene_duration,
            "aspect_ratio": aspect_ratio,
            "video_tone": video_tone,
            "identity": identity,
            "status": "pending",
            "update_at": now,
        },
    )

    initial_state = {
        "creation_uuid": creation_uuid,
        "topic": topic,
        "prompt": topic,
        "platform": platform,
        "platforms": [platform],
        "video_tone": video_tone,
        "num_scenes": num_scenes,
        "scene_duration": scene_duration,
        "aspect_ratio": aspect_ratio,
        "brand_dna": brand_dna,
        "identity": identity,
        "logo_base64": logo_base64,
        "logo_mime_type": logo_mime_type,
    }

    try:
        result = video_agent.invoke(initial_state)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)

    completed_scenes = result.get("completed_scenes", [])
    done_at = datetime.now(timezone.utc).isoformat()

    for scene in completed_scenes:
        generation_uuid = _make_uuid()
        create_generation(
            creation_uuid,
            generation_uuid,
            {
                "uuid": generation_uuid,
                "creation_uuid": creation_uuid,
                "scene_number": scene.get("scene_number"),
                "type": scene.get("type", "value"),
                "video_url": scene.get("video_url", ""),
                "filtered": scene.get("filtered", False),
                "status": "done",
                "create_at": done_at,
            },
        )

    update_creation(creation_uuid, {"status": "active", "update_at": done_at})

    return JsonResponse(
        {
            "uuid": creation_uuid,
            "scenes": completed_scenes,
            "caption": result.get("caption", ""),
            "hashtags": result.get("hashtags", []),
        }
    )
