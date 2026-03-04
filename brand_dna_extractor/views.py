import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .graphs.agent import build_agent

agent = build_agent()


@csrf_exempt
@require_POST
def extract(request):
    body = json.loads(request.body)
    brand_input = body.get("brand_input", "")

    result = agent.invoke({"messages": [], "brand_input": brand_input, "brand_dna": {}})

    return JsonResponse({"brand_dna": result["brand_dna"]})
