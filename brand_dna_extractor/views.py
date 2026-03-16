import json
from django.http import JsonResponse
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, OpenApiResponse, inline_serializer

from .graphs.agent import build_brand_dna_graph
from .models import Brand, BrandDNA
from .serializers import (
    BrandListSerializer, BrandDetailSerializer,
    BrandCreateSerializer, BrandUpdateSerializer,
    BrandDNASerializer, BrandDNACreateSerializer
)
from authentication import (
    SIAJWTAuthentication, SIAAPIKeyAuthentication,
    get_current_user
)
from config.utils import check_ownership
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

# Initialize graph parser
agent = build_brand_dna_graph()


# ============ Brand Endpoints ============

class BrandListView(APIView):
    """List all brands or create a new brand."""
    authentication_classes = [SIAJWTAuthentication, SIAAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Brands'],
        summary='List All Brands',
        description='''
        Get a list of all brands associated with the authenticated user. 
        Data is filtered by `user_id` and `tenant_id` automatically.
        Use query parameters to filter by active status or industry.
        ''',
        parameters=[
            OpenApiParameter(name='is_active', type=bool, location=OpenApiParameter.QUERY, description='Filter by active/inactive status', required=False),
            OpenApiParameter(name='industry', type=str, location=OpenApiParameter.QUERY, description='Search by industry name (case-insensitive)', required=False),
        ],
        responses={200: BrandListSerializer(many=True)},
        examples=[
            OpenApiExample(
                'Brand List Response',
                value=[
                    {
                        "uuid": "a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6",
                        "name": "Nike",
                        "slug": "nike",
                        "industry": "Fashion",
                        "is_active": True,
                        "dna_uuid": "b2c3d4e5-f6g7-h8i9-j0k1-l2m3n4o5p6q7",
                        "logo_url": "https://nike.com/logo.png",
                        "created_at": "2026-03-06T10:00:00Z"
                    }
                ],
                response_only=True
            )
        ]
    )
    def get(self, request):
        user = get_current_user(request)
        queryset = Brand.objects.select_related('dna').all()
        
        if user and user.user_id != 'service':
            queryset = queryset.filter(user_id=user.user_id)

        is_active = request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        industry = request.query_params.get('industry')
        if industry:
            queryset = queryset.filter(industry__icontains=industry)

        serializer = BrandListSerializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        tags=['Brands'],
        summary='Create New Brand',
        description='''
        Create a new brand and optionally provide BrandDNA data in the same request.
        The brand will be automatically associated with the authenticated user.
        If `dna_data` is provided, a new BrandDNA record will be created and linked.
        ''',
        request=BrandCreateSerializer,
        responses={201: BrandDetailSerializer, 400: OpenApiResponse(description='Invalid data provided')},
        examples=[
            OpenApiExample(
                'Complete Brand Creation',
                value={
                    "name": "Tesla",
                    "slug": "tesla",
                    "industry": "Automotive",
                    "page_url": "https://tesla.com",
                    "logo_url": "https://tesla.com/logo.png",
                    "dna_data": {
                        "primary_color": "#E31937",
                        "voice_tone": "Innovative, direct, futuristic",
                        "archetype": "The Visionary",
                        "target_audience": "Tech enthusiasts, eco-conscious drivers"
                    }
                },
                request_only=True
            )
        ]
    )
    def post(self, request):
        user = get_current_user(request)
        serializer = BrandCreateSerializer(data=request.data)
        if serializer.is_valid():
            save_kwargs = {}
            if user and user.user_id != 'service':
                save_kwargs['user_id'] = user.user_id
                if hasattr(user, 'tenant_id') and user.tenant_id:
                    save_kwargs['tenant_id'] = user.tenant_id
            
            brand = serializer.save(**save_kwargs)
                
            return Response(
                BrandDetailSerializer(brand).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BrandDetailView(APIView):
    """Retrieve, update or delete a brand."""
    authentication_classes = [SIAJWTAuthentication, SIAAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Brands'],
        summary='Get Brand Details',
        description='Retrieve full details for a brand, including its nested BrandDNA configuration.',
        responses={
            200: BrandDetailSerializer,
            404: OpenApiResponse(description='Brand not found or access denied')
        },
        examples=[
            OpenApiExample(
                'Brand Detail Response',
                value={
                    "uuid": "a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6",
                    "name": "Tesla",
                    "slug": "tesla",
                    "industry": "Automotive",
                    "dna": {
                        "uuid": "b2c3d4e5-f6g7-h8i9-j0k1-l2m3n4o5p6q7",
                        "primary_color": "#E31937",
                        "voice_tone": "Innovative",
                        "archetype": "The Visionary"
                    },
                    "logo_url": "https://tesla.com/logo.png",
                    "created_at": "2026-03-06T10:00:00Z"
                },
                response_only=True
            )
        ]
    )
    def get(self, request, uuid):
        user = get_current_user(request)
        brand = get_object_or_404(Brand, uuid=uuid)

        if not check_ownership(brand, user):
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        serializer = BrandDetailSerializer(brand)
        return Response(serializer.data)

    @extend_schema(
        tags=['Brands'],
        summary='Update Brand',
        description='Update existing brand fields. Only the fields provided will be modified.',
        request=BrandUpdateSerializer,
        responses={200: BrandDetailSerializer, 403: OpenApiResponse(description='Permission denied')}
    )
    def patch(self, request, uuid):
        user = get_current_user(request)
        brand = get_object_or_404(Brand, uuid=uuid)

        if not check_ownership(brand, user):
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        serializer = BrandUpdateSerializer(brand, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(BrandDetailSerializer(brand).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=['Brands'],
        summary='Delete Brand',
        description='Delete a brand and all associated data.',
        responses={204: OpenApiResponse(description='Deleted successfully')}
    )
    def delete(self, request, uuid):
        user = get_current_user(request)
        brand = get_object_or_404(Brand, uuid=uuid)

        if not check_ownership(brand, user):
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        brand.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ============ Brand DNA Endpoints ============

class BrandDNAListView(APIView):
    """List all Brand DNA records or create a new one."""
    authentication_classes = [SIAJWTAuthentication, SIAAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Brand DNA'],
        summary='List All Brand DNA',
        description='Get a list of all Brand DNA configurations across all brands.',
        responses={200: BrandDNASerializer(many=True)}
    )
    def get(self, request):
        queryset = BrandDNA.objects.all()
        serializer = BrandDNASerializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        tags=['Brand DNA'],
        summary='Create Brand DNA',
        description='''
        Create a standalone Brand DNA configuration. 
        Note: It is usually better to create DNA through the Brand creation endpoint.
        ''',
        request=BrandDNACreateSerializer,
        responses={201: BrandDNASerializer}
    )
    def post(self, request):
        serializer = BrandDNACreateSerializer(data=request.data)
        if serializer.is_valid():
            dna = serializer.save()
            return Response(BrandDNASerializer(dna).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BrandDNADetailView(APIView):
    """Retrieve, update or delete a Brand DNA record."""
    authentication_classes = [SIAJWTAuthentication, SIAAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Brand DNA'],
        summary='Get Brand DNA Details',
        responses={200: BrandDNASerializer, 404: OpenApiResponse(description='Not found')}
    )
    def get(self, request, uuid):
        dna = get_object_or_404(BrandDNA, uuid=uuid)
        serializer = BrandDNASerializer(dna)
        return Response(serializer.data)

    @extend_schema(
        tags=['Brand DNA'],
        summary='Update Brand DNA',
        description='Update Brand DNA configuration. Partial updates supported.',
        request=BrandDNACreateSerializer,
        responses={200: BrandDNASerializer}
    )
    def patch(self, request, uuid):
        dna = get_object_or_404(BrandDNA, uuid=uuid)
        serializer = BrandDNACreateSerializer(dna, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(BrandDNASerializer(dna).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=['Brand DNA'],
        summary='Delete Brand DNA',
        responses={204: OpenApiResponse(description='Deleted successfully')}
    )
    def delete(self, request, uuid):
        dna = get_object_or_404(BrandDNA, uuid=uuid)
        dna.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class BrandDNAByBrandView(APIView):
    """Get or update Brand DNA for a specific brand."""
    authentication_classes = [SIAJWTAuthentication, SIAAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Brand DNA'],
        summary='Get Brand DNA by Brand',
        description='Retrieve the DNA configuration specifically linked to a given brand UUID.',
        parameters=[
            OpenApiParameter(name='brand_uuid', type=str, location=OpenApiParameter.PATH, description='UUID of the parent brand')
        ],
        responses={
            200: BrandDNASerializer,
            404: OpenApiResponse(description='Brand or DNA not found')
        }
    )
    def get(self, request, brand_uuid):
        user = get_current_user(request)
        brand = get_object_or_404(Brand, uuid=brand_uuid)
        if not check_ownership(brand, user):
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
            
        if not brand.dna:
            return Response({"error": "No DNA found"}, status=status.HTTP_404_NOT_FOUND)
            
        serializer = BrandDNASerializer(brand.dna)
        return Response(serializer.data)

    @extend_schema(
        tags=['Brand DNA'],
        summary='Update Brand DNA by Brand',
        description="Update a specific brand's DNA configuration.",
        request=BrandDNACreateSerializer,
        responses={200: BrandDNASerializer}
    )
    def patch(self, request, brand_uuid):
        user = get_current_user(request)
        brand = get_object_or_404(Brand, uuid=brand_uuid)
        if not check_ownership(brand, user):
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        if not brand.dna:
            return Response({"error": "No DNA found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = BrandDNACreateSerializer(brand.dna, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(BrandDNASerializer(brand.dna).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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
    description='Scrapes the provided brand URL to extract and process color palettes, typography, voice tone, archetype, target audience, and industry via a LangGraph AI workflow. Results are saved in the DB natively tied to the authenticated creator.',
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
                            "archetype": "The Hero",
                            "target_audience": "Athletes and fitness enthusiasts who value performance and style",
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
