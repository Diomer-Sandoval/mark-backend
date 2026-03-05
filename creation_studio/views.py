import json
import random
import string
from datetime import datetime, timezone

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .graphs.agent import build_agent
from .graphs.utils.firebase_utils import create_creation, create_generation, update_creation

agent = build_agent()


def _make_uuid(length: int = 17) -> str:
    chars = string.ascii_letters + string.digits
    return "".join(random.choices(chars, k=length))


@csrf_exempt
@require_POST
def generate_content(request):
    body = json.loads(request.body)
    now = datetime.now(timezone.utc).isoformat()
    creation_uuid = _make_uuid()

    create_creation(creation_uuid, {
        "uuid": creation_uuid,
        "creation_at": now,
        "platforms": body.get("platform", []),
        "post_type": body.get("post_type", ""),
        "post_tone": body.get("post_tone", ""),
        "identity": body.get("company", ""),
        "status": "pending",
        "update_at": now,
    })

    initial_state = {
        "creation_uuid": creation_uuid,
        "company": body.get("company", "Unknown"),
        "topic": body.get("topic", ""),
        "platform": body.get("platform", "Instagram"),
        "post_type": body.get("post_type", "Post"),
        "post_tone": body.get("post_tone", "General"),
        "brand_tone": body.get("brand_tone", ""),
        "brand_dna": body.get("brand_dna", {}),
    }

    result = agent.invoke(initial_state)

    image_url = result.get("image_url", "")
    generation_uuid = result.get("generation_uuid", "")
    done_at = datetime.now(timezone.utc).isoformat()

    if generation_uuid:
        create_generation(creation_uuid, generation_uuid, {
            "uuid": generation_uuid,
            "creation_uuid": creation_uuid,
            "img_url": image_url,
            "prompt": result.get("image_prompt", ""),
            "status": "done",
            "create_at": done_at,
        })

    update_creation(creation_uuid, {"status": "active", "update_at": done_at})

    return JsonResponse({
        "uuid": creation_uuid,
        "strategy": result.get("strategy", ""),
        "image_prompt": result.get("image_prompt", ""),
        "image_url": image_url,
    })
