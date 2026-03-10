import json
from django.http import JsonResponse
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse, inline_serializer

from .graphs.agent import build_brand_dna_graph

# Initialize graph parser
agent = build_brand_dna_graph()

# Create inline serializer definition for the request body schema
ExtractRequestSerializer = inline_serializer(
    name='ExtractBrandRequest',
    fields={
        'brand_input': serializers.URLField(
            help_text="The Website URL of the brand to scrape and analyze (e.g. 'https://www.apple.com/')",
            required=True
        )
    }
)

# Create serializers for the responses to ensure Swagger displays them correctly
SuccessResponseSerializer = inline_serializer(
    name='ExtractSuccessResponse',
    fields={
        'status': serializers.CharField(default='success'),
        'brand_id': serializers.UUIDField(),
        'db_saved': serializers.BooleanField(),
        'brand_dna': serializers.DictField(child=serializers.CharField())
    }
)

ErrorResponseSerializer = inline_serializer(
    name='ExtractErrorResponse',
    fields={
        'status': serializers.CharField(default='error'),
        'message': serializers.CharField()
    }
)

@extend_schema(
    tags=['Brand DNA Extractor'],
    summary='Extract Brand DNA via AI Agent',
    description='Scrapes the provided brand URL to extract and process color palettes, typography, voice tone, metadata, and industry via a LangGraph AI workflow. Results are saved in the DB natively tied to the authenticated creator.',
    request=ExtractRequestSerializer,
    responses={
        200: OpenApiResponse(
            response=SuccessResponseSerializer,
            description='Successful Extraction',
            examples=[
                OpenApiExample(
                    'Success Example',
                    value={
                        "status": "success",
                        "brand_id": "98ba89a4-6ff9-4a1d-9d55-e8e8d0a74644",
                        "brand_dna": {
                            "brand_name": "Nike",
                            "industry": "Footwear and Apparel",
                            "primary_color": "#111111",
                            "secondary_color": "#FFFFFF",
                            "accent_color": "#E5E5E5",
                            "complementary_color": "#000000",
                            "font_body_family": "Helvetica",
                            "font_headings_family": "Helvetica Neue",
                            "voice_tone": "Inspirational, Bold, Athletic",
                            "keywords": "shoes, sports, fitness, clothes",
                            "description": "Nike delivers innovative products, experiences and services to inspire athletes."
                        },
                        "db_saved": True
                    }
                )
            ]
        ),
        400: OpenApiResponse(
            response=ErrorResponseSerializer,
            description='Validation Error or Agent Error',
            examples=[
                OpenApiExample(
                    'Error Example',
                    value={
                        "status": "error",
                        "message": "Invalid URL format or Agent failed to extract data."
                    }
                )
            ]
        ),
        500: OpenApiResponse(
            response=ErrorResponseSerializer,
            description='Internal Server Error',
            examples=[
                OpenApiExample(
                    'Server Error Example',
                    value={
                        "status": "error",
                        "message": "Internal processing exception."
                    }
                )
            ]
        )
    }
)
@api_view(['POST'])
@permission_classes([AllowAny]) # We allow any for easy testing, but token gets parsed if present
def extract(request):
    try:
        # Request.data handles json natively
        brand_input = request.data.get("brand_input", "") 
        
        # If authenticated via SIAJWTAuthentication, fetch user/tenant info
        # The JWT middleware populated request.user
        user_id = getattr(request.user, "user_id", None)
        tenant_id = getattr(request.user, "tenant_id", None)

        # Execute the Agentic Workflow passing context
        result = agent.invoke({
            "input_url": brand_input,
            "user_id": user_id,
            "tenant_id": tenant_id,
            "scraper_result": {},
            "preprocessed_data": "",
            "llm_output": {},
            "db_saved": False,
            "error": None
        })

        if result.get("error"):
            return JsonResponse({"status": "error", "message": result.get("error")}, status=400)

        return JsonResponse({
            "status": "success", 
            "brand_id": result.get("brand_id"),
            "brand_dna": result.get("llm_output", {}),
            "db_saved": result.get("db_saved", False)
        })
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
