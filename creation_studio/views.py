import json
import random
import string
from datetime import datetime, timezone

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .graphs.create_post import build_agent, build_copy_agent
from .graphs.edit_image import build_edit_image_agent
from .graphs.utils.firebase_utils import (
    create_creation,
    create_generation,
    update_creation,
)

agent = build_agent()
copy_agent = build_copy_agent()
edit_image_agent = build_edit_image_agent()


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
    brand_dna = body.get("brand_dna", {})
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
