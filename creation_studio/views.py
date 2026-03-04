import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from langchain_core.messages import HumanMessage

from .graphs.agent import build_agent

agent = build_agent()


@csrf_exempt
@require_POST
def chat(request):
    body = json.loads(request.body)
    message = body.get("message", "")

    result = agent.invoke({"messages": [HumanMessage(content=message)]})

    response_text = result["messages"][-1].content
    return JsonResponse({"response": response_text})
