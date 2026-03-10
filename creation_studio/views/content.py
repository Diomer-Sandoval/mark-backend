import json
import random
import string
from datetime import datetime, timezone

from django.http import JsonResponse
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse, inline_serializer

from ..graphs.create_post import build_agent, build_copy_agent
from ..graphs.edit_image import build_edit_image_agent
from ..graphs.create_carousel.agent import build_carousel_agent
from ..graphs.create_carousel.nodes.generate_slides.slide_prompt_engineer import build_slide_prompt
from ..graphs.create_carousel.nodes.generate_slides.slide_qc_validator import validate_slide
from ..graphs.create_carousel.nodes.generate_slides.node import MAX_RETRIES
from ..graphs.create_video.agent import build_video_agent
from ..graphs.utils.gemini_utils import generate_image_with_logo
from ..graphs.utils.cloudinary_utils import upload_image
from ..graphs.utils.firebase_utils import (
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


# ---------------------------------------------------------------------------
# Shared inline serializer fields
# ---------------------------------------------------------------------------

_brand_dna_field = serializers.DictField(
    child=serializers.CharField(),
    help_text="Brand DNA object (colors, typography, voice_tone, keywords, etc.)",
    required=False,
)

_identity_field = serializers.DictField(
    child=serializers.CharField(),
    help_text="Brand identity object (name, logo_url, etc.)",
    required=False,
)

_logo_fields = {
    "logo_base64": serializers.CharField(
        required=False,
        help_text="Base64-encoded logo image (takes priority over logo_url)",
    ),
    "logo_mime_type": serializers.CharField(
        required=False,
        default="image/png",
        help_text="MIME type of the base64 logo (e.g. image/png, image/svg+xml)",
    ),
    "logo_url": serializers.URLField(
        required=False,
        help_text="Public URL of the logo (used when logo_base64 is not provided)",
    ),
}


# ---------------------------------------------------------------------------
# generate_content — POST /api/content/generate-image/
# ---------------------------------------------------------------------------

@extend_schema(
    tags=["Content Generation"],
    summary="Generate an AI image + copy for a social media post",
    description=(
        "Runs the create-post LangGraph agent to produce a platform-optimised image "
        "and marketing copy based on the supplied prompt, brand DNA, and identity."
    ),
    request=inline_serializer(
        name="GenerateContentRequest",
        fields={
            "prompt": serializers.CharField(help_text="Creative brief / topic for the post"),
            "platforms": serializers.ListField(
                child=serializers.CharField(),
                default=["instagram"],
                help_text="Target social platforms (e.g. ['instagram', 'linkedin'])",
            ),
            "post_type": serializers.CharField(default="post", required=False),
            "post_tone": serializers.CharField(default="promotional", required=False),
            "brand_dna": _brand_dna_field,
            "identity": _identity_field,
            **_logo_fields,
        },
    ),
    responses={
        200: OpenApiResponse(
            response=inline_serializer(
                name="GenerateContentResponse",
                fields={
                    "uuid": serializers.CharField(help_text="Creation UUID"),
                    "copy": serializers.CharField(help_text="Generated marketing copy"),
                    "image_url": serializers.URLField(help_text="URL of the generated image"),
                },
            ),
            description="Image and copy generated successfully",
            examples=[
                OpenApiExample(
                    "Success",
                    value={
                        "uuid": "aBcDeFgHiJkLmNo1",
                        "copy": "Feel the difference. #Nike #JustDoIt",
                        "image_url": "https://res.cloudinary.com/demo/image/upload/sample.jpg",
                    },
                )
            ],
        ),
        500: OpenApiResponse(description="Agent error"),
    },
)
@api_view(["POST"])
@permission_classes([AllowAny])
def generate_content(request):
    try:
        body = request.data
    except Exception as e:
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


# ---------------------------------------------------------------------------
# regenerate_copy — POST /api/content/edit-copy/
# ---------------------------------------------------------------------------

@extend_schema(
    tags=["Content Generation"],
    summary="Regenerate marketing copy with optional feedback",
    description=(
        "Re-runs the copywriter agent to produce revised copy for an existing creation, "
        "optionally incorporating user feedback on the previous version."
    ),
    request=inline_serializer(
        name="RegenerateCopyRequest",
        fields={
            "creation_uuid": serializers.CharField(help_text="UUID of the existing creation"),
            "prompt": serializers.CharField(help_text="Original creative brief"),
            "current_copy": serializers.CharField(required=False, help_text="Copy to be revised"),
            "copy_feedback": serializers.CharField(required=False, help_text="User feedback on current copy"),
            "platforms": serializers.ListField(child=serializers.CharField(), default=["instagram"]),
            "post_type": serializers.CharField(default="post", required=False),
            "post_tone": serializers.CharField(default="promotional", required=False),
            "brand_dna": _brand_dna_field,
            "identity": _identity_field,
        },
    ),
    responses={
        200: OpenApiResponse(
            response=inline_serializer(
                name="RegenerateCopyResponse",
                fields={
                    "uuid": serializers.CharField(),
                    "copy": serializers.CharField(),
                },
            ),
            description="Copy regenerated successfully",
            examples=[
                OpenApiExample(
                    "Success",
                    value={"uuid": "aBcDeFgHiJkLmNo1", "copy": "Elevate your game. #Nike"},
                )
            ],
        ),
        500: OpenApiResponse(description="Agent error"),
    },
)
@api_view(["POST"])
@permission_classes([AllowAny])
def regenerate_copy(request):
    try:
        body = request.data
    except Exception as e:
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


# ---------------------------------------------------------------------------
# edit_image — POST /api/content/edit-image/
# ---------------------------------------------------------------------------

@extend_schema(
    tags=["Content Generation"],
    summary="Edit an existing generated image",
    description=(
        "Runs the edit-image LangGraph agent to apply the provided prompt as an edit "
        "instruction to an existing image identified by its URL."
    ),
    request=inline_serializer(
        name="EditImageRequest",
        fields={
            "creation_uuid": serializers.CharField(help_text="UUID of the parent creation"),
            "uuid": serializers.CharField(help_text="UUID of the generation to edit (parent_uuid)"),
            "prompt": serializers.CharField(help_text="Edit instruction (e.g. 'make the background blue')"),
            "img_url": serializers.URLField(help_text="URL of the image to edit"),
        },
    ),
    responses={
        200: OpenApiResponse(
            response=inline_serializer(
                name="EditImageResponse",
                fields={
                    "status": serializers.CharField(),
                    "message": serializers.CharField(),
                    "img_url": serializers.URLField(),
                },
            ),
            description="Image edited successfully",
            examples=[
                OpenApiExample(
                    "Success",
                    value={
                        "status": "ok",
                        "message": "Image edited successfully",
                        "img_url": "https://res.cloudinary.com/demo/image/upload/edited.jpg",
                    },
                )
            ],
        ),
        500: OpenApiResponse(description="Agent error"),
    },
)
@api_view(["POST"])
@permission_classes([AllowAny])
def edit_image(request):
    body = request.data
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


# ---------------------------------------------------------------------------
# generate_carousel — POST /api/content/generate-carousel/
# ---------------------------------------------------------------------------

@extend_schema(
    tags=["Content Generation"],
    summary="Generate a multi-slide carousel",
    description=(
        "Runs the create-carousel LangGraph agent to produce a set of branded slide images "
        "with headlines, caption, and hashtags for the requested platform."
    ),
    request=inline_serializer(
        name="GenerateCarouselRequest",
        fields={
            "topic": serializers.CharField(help_text="Topic / creative brief for the carousel"),
            "platform": serializers.CharField(default="instagram", required=False),
            "post_tone": serializers.CharField(default="educational", required=False),
            "num_slides": serializers.IntegerField(
                default=7,
                required=False,
                help_text="Number of slides (clamped to 5–10)",
            ),
            "brand_dna": _brand_dna_field,
            "identity": _identity_field,
            **_logo_fields,
        },
    ),
    responses={
        200: OpenApiResponse(
            response=inline_serializer(
                name="GenerateCarouselResponse",
                fields={
                    "uuid": serializers.CharField(),
                    "slides": serializers.ListField(
                        child=serializers.DictField(),
                        help_text="List of slide objects (index, headline, image_url, qc_passed, qc_attempts)",
                    ),
                    "caption": serializers.CharField(),
                    "hashtags": serializers.ListField(child=serializers.CharField()),
                },
            ),
            description="Carousel generated successfully",
            examples=[
                OpenApiExample(
                    "Success",
                    value={
                        "uuid": "aBcDeFgHiJkLmNo1",
                        "slides": [
                            {
                                "index": 0,
                                "headline": "5 Tips to Boost Your Brand",
                                "image_url": "https://res.cloudinary.com/demo/image/upload/slide0.jpg",
                                "qc_passed": True,
                                "qc_attempts": 1,
                            }
                        ],
                        "caption": "Boost your brand with these 5 actionable tips!",
                        "hashtags": ["#Branding", "#Marketing"],
                    },
                )
            ],
        ),
        500: OpenApiResponse(description="Agent error"),
    },
)
@api_view(["POST"])
@permission_classes([AllowAny])
def generate_carousel(request):
    try:
        body = request.data
    except Exception as e:
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
        "prompt": topic,
        "platform": platform,
        "platforms": [platform],
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


# ---------------------------------------------------------------------------
# edit_carousel_slide — POST /api/content/edit-carousel-slide/
# ---------------------------------------------------------------------------

@extend_schema(
    tags=["Content Generation"],
    summary="Re-generate a single carousel slide",
    description=(
        "Re-runs image generation for one slide of an existing carousel, optionally "
        "incorporating user feedback. Includes QC validation with automatic retries."
    ),
    request=inline_serializer(
        name="EditCarouselSlideRequest",
        fields={
            "creation_uuid": serializers.CharField(help_text="UUID of the parent carousel creation"),
            "slide": serializers.DictField(
                help_text="Slide object: {index, headline, body, visual_description}"
            ),
            "visual_theme": serializers.CharField(required=False, help_text="Visual theme override"),
            "brand_dna": _brand_dna_field,
            "platform": serializers.CharField(default="instagram", required=False),
            "feedback": serializers.CharField(required=False, help_text="User feedback on the previous image"),
            **_logo_fields,
        },
    ),
    responses={
        200: OpenApiResponse(
            response=inline_serializer(
                name="EditCarouselSlideResponse",
                fields={
                    "uuid": serializers.CharField(),
                    "slide": serializers.DictField(
                        help_text="Updated slide: {index, headline, image_url, qc_passed, qc_attempts}"
                    ),
                },
            ),
            description="Slide regenerated successfully",
            examples=[
                OpenApiExample(
                    "Success",
                    value={
                        "uuid": "aBcDeFgHiJkLmNo1",
                        "slide": {
                            "index": 2,
                            "headline": "Step 3: Consistency",
                            "image_url": "https://res.cloudinary.com/demo/image/upload/slide2.jpg",
                            "qc_passed": True,
                            "qc_attempts": 2,
                        },
                    },
                )
            ],
        ),
        500: OpenApiResponse(description="Generation or upload error"),
    },
)
@api_view(["POST"])
@permission_classes([AllowAny])
def edit_carousel_slide(request):
    try:
        body = request.data
    except Exception as e:
        return JsonResponse({"error": f"Invalid JSON: {e}"}, status=400)

    creation_uuid = body.get("creation_uuid", "")
    slide = body.get("slide", {})
    visual_theme = body.get("visual_theme", "")
    brand_dna = body.get("brand_dna", {})
    platform = body.get("platform", "instagram")
    feedback = body.get("feedback", "")

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


# ---------------------------------------------------------------------------
# generate_video — POST /api/content/generate-video/
# ---------------------------------------------------------------------------

@extend_schema(
    tags=["Content Generation"],
    summary="Generate a multi-scene video",
    description=(
        "Runs the create-video LangGraph agent to produce a set of branded video scenes "
        "with caption and hashtags for the requested platform."
    ),
    request=inline_serializer(
        name="GenerateVideoRequest",
        fields={
            "topic": serializers.CharField(help_text="Topic / creative brief for the video"),
            "platform": serializers.ChoiceField(
                choices=["Instagram Reels", "TikTok", "YouTube Shorts", "LinkedIn", "Facebook", "YouTube"],
                default="Instagram Reels",
                required=False,
            ),
            "video_tone": serializers.CharField(default="General", required=False),
            "num_scenes": serializers.IntegerField(
                default=4,
                required=False,
                help_text="Number of scenes (clamped to 3–6)",
            ),
            "scene_duration": serializers.ChoiceField(
                choices=[5, 6, 8],
                default=6,
                required=False,
                help_text="Duration per scene in seconds (5, 6, or 8)",
            ),
            "brand_dna": _brand_dna_field,
            "identity": _identity_field,
            **_logo_fields,
        },
    ),
    responses={
        200: OpenApiResponse(
            response=inline_serializer(
                name="GenerateVideoResponse",
                fields={
                    "uuid": serializers.CharField(),
                    "scenes": serializers.ListField(
                        child=serializers.DictField(),
                        help_text="List of scene objects (scene_number, type, video_url, filtered)",
                    ),
                    "caption": serializers.CharField(),
                    "hashtags": serializers.ListField(child=serializers.CharField()),
                },
            ),
            description="Video scenes generated successfully",
            examples=[
                OpenApiExample(
                    "Success",
                    value={
                        "uuid": "aBcDeFgHiJkLmNo1",
                        "scenes": [
                            {
                                "scene_number": 1,
                                "type": "value",
                                "video_url": "https://res.cloudinary.com/demo/video/upload/scene1.mp4",
                                "filtered": False,
                            }
                        ],
                        "caption": "Discover the future of marketing.",
                        "hashtags": ["#Marketing", "#AI"],
                    },
                )
            ],
        ),
        500: OpenApiResponse(description="Agent error"),
    },
)
@api_view(["POST"])
@permission_classes([AllowAny])
def generate_video(request):
    try:
        body = request.data
    except Exception as e:
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
