"""
Core API Views for Creation Studio.

Provides REST endpoints for:
- Brands and Brand DNA
- Creations and Generations
- Previews and Preview Items
- Posts and Platform Insights

All endpoints require authentication via SIA Solutions JWT or API Key.
Data is automatically filtered to show only the current user's records.
"""

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse, OpenApiExample

from ..models import (
    Brand, BrandDNA, Creation, Generation,
    Preview, PreviewItem, Post, PlatformInsight
)
from ..auth import (
    SIAJWTAuthentication, SIAAPIKeyAuthentication,
    get_current_user
)
from ..serializers import (
    # Brand
    BrandListSerializer, BrandDetailSerializer,
    BrandCreateSerializer, BrandUpdateSerializer,
    # BrandDNA
    BrandDNASerializer, BrandDNACreateSerializer,
    # Creation
    CreationListSerializer, CreationDetailSerializer,
    CreationCreateSerializer, CreationUpdateSerializer,
# Removed CreationSearchRequestSerializer,
    # Generation
    GenerationListSerializer, GenerationDetailSerializer,
    GenerationCreateSerializer, GenerationUpdateSerializer,
    # Preview
    PreviewDetailSerializer, PreviewCreateSerializer,
    PreviewItemSerializer,
    # Post
    PostListSerializer, PostDetailSerializer,
    PostCreateSerializer, PostUpdateSerializer,
    PostMetricsUpdateSerializer,
    # Platform Insight
    PlatformInsightSerializer, PlatformInsightCreateSerializer,
    PlatformInsightBulkCreateSerializer,
)
from .content import (
    agent as _image_agent,
    copy_agent as _copy_agent,
    edit_image_agent as _edit_image_agent,
    carousel_agent as _carousel_agent,
    video_agent as _video_agent,
    _resolve_logo,
    _ASPECT_RATIO_MAP,
)
from ..graphs.create_carousel.nodes.generate_slides.slide_prompt_engineer import build_slide_prompt
from ..graphs.create_carousel.nodes.generate_slides.slide_qc_validator import validate_slide
from ..graphs.create_carousel.nodes.generate_slides.node import MAX_RETRIES
from ..graphs.utils.gemini_utils import generate_image_with_logo
from ..graphs.utils.cloudinary_utils import upload_image


def check_ownership(obj, user):
    """Check if user owns this object or is super admin."""
    if not user:
        return False
    if user.user_id == 'service':
        return True
    if hasattr(obj, 'user_id') and obj.user_id == user.user_id:
        return True
    if hasattr(obj, 'tenant_id') and user.tenant_id and obj.tenant_id == user.tenant_id:
        return True
    
    # Hierarchical checks
    if isinstance(obj, Creation) and obj.brand:
        return check_ownership(obj.brand, user)
    if isinstance(obj, Generation) and obj.creation:
        return check_ownership(obj.creation, user)
    if isinstance(obj, PlatformInsight) and obj.brand:
        return check_ownership(obj.brand, user)
    
    return False


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
        queryset = Brand.objects.all()
        
        if user and user.user_id != 'service':
            queryset = queryset.filter(user_id=user.user_id)
            if user.tenant_id:
                queryset = queryset.filter(tenant_id=user.tenant_id)

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
            if user and user.user_id != 'service':
                brand = serializer.save(user_id=user.user_id, tenant_id=user.tenant_id)
            else:
                brand = serializer.save()
                
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


# ============ Creation Endpoints ============

class CreationListView(APIView):
    """List all creations or create a new creation project."""
    authentication_classes = [SIAJWTAuthentication, SIAAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Creations'],
        summary='List All Creations',
        description='''
        Get a list of all creation projects. 
        Projects are grouped by brand and can represent single posts, carousels, or video projects.
        Use filters to narrow down by brand, current status, or the type of post being created.
        ''',
        parameters=[
            OpenApiParameter(name='brand_uuid', type=str, location=OpenApiParameter.QUERY, description='Filter by brand UUID', required=False),
            OpenApiParameter(name='status', type=str, location=OpenApiParameter.QUERY, description='Filter by status (pending, active, archived)', required=False),
            OpenApiParameter(name='post_type', type=str, location=OpenApiParameter.QUERY, description='Filter by post type (post, carousel, video)', required=False),
        ],
        responses={200: CreationListSerializer(many=True)},
        examples=[
            OpenApiExample(
                'Creation List Response',
                value=[
                    {
                        "uuid": "c1d2e3f4-g5h6-i7j8-k9l0-m1n2o3p4q5r6",
                        "brand_uuid": "a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6",
                        "brand_name": "Nike",
                        "title": "Summer Campaign 2026",
                        "post_type": "carousel",
                        "status": "active",
                        "platforms": "instagram,facebook",
                        "created_at": "2026-03-10T12:00:00Z"
                    }
                ],
                response_only=True
            )
        ]
    )
    def get(self, request):
        user = get_current_user(request)
        queryset = Creation.objects.all()

        if user and user.user_id != 'service':
            queryset = queryset.filter(brand__user_id=user.user_id)

        brand_uuid = request.query_params.get('brand_uuid')
        if brand_uuid:
            queryset = queryset.filter(brand__uuid=brand_uuid)

        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        post_type = request.query_params.get('post_type')
        if post_type:
            queryset = queryset.filter(post_type=post_type)

        serializer = CreationListSerializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        tags=['Creations'],
        summary='Create New Creation',
        description='''
        Start a new creation project linked to a specific brand.
        This provides the container for all future AI generations (images, videos, copy).
        ''',
        request=CreationCreateSerializer,
        responses={201: CreationDetailSerializer, 403: OpenApiResponse(description='Brand ownership required')},
        examples=[
            OpenApiExample(
                'Create Creation Request',
                value={
                    "brand": "a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6",
                    "title": "Nike Air Launch",
                    "post_type": "post",
                    "status": "pending",
                    "platforms": "instagram,tiktok",
                    "post_tone": "vibrant, high-energy"
                },
                request_only=True
            )
        ]
    )
    def post(self, request):
        user = get_current_user(request)
        serializer = CreationCreateSerializer(data=request.data)
        if serializer.is_valid():
            brand = serializer.validated_data.get('brand')
            if brand and not check_ownership(brand, user):
                return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
                
            creation = serializer.save()
            return Response(CreationDetailSerializer(creation).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CreationDetailView(APIView):
    """Retrieve, update or delete a creation project."""
    authentication_classes = [SIAJWTAuthentication, SIAAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Creations'],
        summary='Get Creation Details',
        description='Get full details of a creation including nested generations.',
        responses={200: CreationDetailSerializer, 404: OpenApiResponse(description='Not found')}
    )
    def get(self, request, uuid):
        user = get_current_user(request)
        creation = get_object_or_404(Creation, uuid=uuid)
        if not check_ownership(creation, user):
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
            
        serializer = CreationDetailSerializer(creation)
        return Response(serializer.data)

    @extend_schema(
        tags=['Creations'],
        summary='Update Creation',
        request=CreationUpdateSerializer,
        responses={200: CreationDetailSerializer}
    )
    def patch(self, request, uuid):
        user = get_current_user(request)
        creation = get_object_or_404(Creation, uuid=uuid)
        if not check_ownership(creation, user):
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        serializer = CreationUpdateSerializer(creation, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(CreationDetailSerializer(creation).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=['Creations'],
        summary='Delete Creation',
        responses={204: OpenApiResponse(description='Deleted successfully')}
    )
    def delete(self, request, uuid):
        user = get_current_user(request)
        creation = get_object_or_404(Creation, uuid=uuid)
        if not check_ownership(creation, user):
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        creation.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ============ Generation Endpoints ============

_GENERATION_VALID_TYPES = ["image", "carousel", "video"]


def _brand_context_from_creation(creation) -> tuple[dict, dict]:
    """Return (brand_dna, identity) dicts built from the creation's brand."""
    brand = creation.brand
    if not brand:
        return {}, {}

    identity = {
        "name": brand.name,
        "logo_url": brand.logo_url,
        "page_url": brand.page_url,
        "industry": brand.industry,
    }

    dna = brand.dna
    brand_dna = {}
    if dna:
        brand_dna = {
            "primary_color": dna.primary_color,
            "secondary_color": dna.secondary_color,
            "accent_color": dna.accent_color,
            "complementary_color": dna.complementary_color,
            "font_body_family": dna.font_body_family,
            "font_headings_family": dna.font_headings_family,
            "voice_tone": dna.voice_tone,
            "keywords": dna.keywords,
            "description": dna.description,
        }

    return brand_dna, identity

# Maps Creation.post_type → generation pipeline type
_POST_TYPE_TO_PIPELINE = {
    "post": "image",
    "story": "image",
    "infographic": "image",
    "carousel": "carousel",
    "reel": "video",
}


def _pipeline_image(creation, body: dict):
    """Run the image pipeline and persist to ORM. Returns (Generation, extra_dict)."""
    db_brand_dna, db_identity = _brand_context_from_creation(creation)
    creation_platforms = [p for p in creation.platforms.split(",") if p.strip()] if creation.platforms else ["instagram"]
    initial_state = {
        "creation_uuid": str(creation.uuid),
        "prompt": body.get("prompt", creation.original_prompt),
        "platforms": body.get("platforms", creation_platforms),
        "post_type": body.get("post_type", creation.post_type or "post"),
        "post_tone": body.get("post_tone", creation.post_tone or "promotional"),
        "brand_dna": body.get("brand_dna", db_brand_dna),
        "identity": body.get("identity", db_identity),
    }
    result = _image_agent.invoke(initial_state)

    image_url = result.get("image_url", "")
    image_prompt = result.get("image_prompt", body.get("prompt", ""))

    strategy_raw = result.get("strategy", "")
    if "---" in strategy_raw:
        _, copy_part = strategy_raw.split("---", 1)
        copy_part = copy_part.strip()
    else:
        copy_part = strategy_raw

    generation = Generation.objects.create(
        creation=creation,
        media_type="image",
        prompt=image_prompt,
        status="done",
        generation_params={"platforms": initial_state["platforms"]},
    )
    if image_url:
        MediaFile.objects.create(
            generation=generation,
            url=image_url,
            file_type="image/jpeg",
        )
    return generation, {"copy": copy_part}


def _pipeline_carousel(creation, body: dict):
    """Run the carousel pipeline and persist to ORM. Returns (list[Generation], extra_dict)."""
    db_brand_dna, db_identity = _brand_context_from_creation(creation)
    logo_base64, logo_mime_type = _resolve_logo({**{"logo_url": db_identity.get("logo_url", "")}, **body})
    creation_platform = creation.platforms.split(",")[0].strip() if creation.platforms else "instagram"
    platform = body.get("platform", creation_platform)
    num_slides = max(5, min(10, int(body.get("num_slides", 7))))

    initial_state = {
        "creation_uuid": str(creation.uuid),
        "topic": body.get("prompt", creation.original_prompt),
        "prompt": body.get("prompt", creation.original_prompt),
        "platform": platform,
        "platforms": [platform],
        "post_tone": body.get("post_tone", creation.post_tone or "educational"),
        "num_slides": num_slides,
        "brand_dna": body.get("brand_dna", db_brand_dna),
        "identity": body.get("identity", db_identity),
        "logo_base64": logo_base64,
        "logo_mime_type": logo_mime_type,
    }
    result = _carousel_agent.invoke(initial_state)

    completed_slides = result.get("completed_slides", [])
    generations = []
    for slide in completed_slides:
        gen = Generation.objects.create(
            creation=creation,
            media_type="image",
            prompt=slide.get("headline", ""),
            status="done",
            generation_params={
                "slide_index": slide.get("index"),
                "headline": slide.get("headline", ""),
                "qc_passed": slide.get("qc_passed", False),
                "qc_attempts": slide.get("qc_attempts", 1),
            },
        )
        if slide.get("image_url"):
            MediaFile.objects.create(
                generation=gen,
                url=slide["image_url"],
                file_type="image/jpeg",
            )
        generations.append(gen)

    return generations, {
        "caption": result.get("caption", ""),
        "hashtags": result.get("hashtags", []),
    }


def _pipeline_video(creation, body: dict):
    """Run the video pipeline and persist to ORM. Returns (list[Generation], extra_dict)."""
    db_brand_dna, db_identity = _brand_context_from_creation(creation)
    logo_base64, logo_mime_type = _resolve_logo({**{"logo_url": db_identity.get("logo_url", "")}, **body})
    creation_platform = creation.platforms.split(",")[0].strip() if creation.platforms else "Instagram Reels"
    platform = body.get("platform", creation_platform)
    num_scenes = max(3, min(6, int(body.get("num_scenes", 4))))
    scene_duration = int(body.get("scene_duration", 6))
    if scene_duration not in (5, 6, 8):
        scene_duration = 6

    initial_state = {
        "creation_uuid": str(creation.uuid),
        "topic": body.get("prompt", creation.original_prompt),
        "prompt": body.get("prompt", creation.original_prompt),
        "platform": platform,
        "platforms": [platform],
        "video_tone": body.get("video_tone", creation.post_tone or "General"),
        "num_scenes": num_scenes,
        "scene_duration": scene_duration,
        "aspect_ratio": _ASPECT_RATIO_MAP.get(platform.lower(), "9:16"),
        "brand_dna": body.get("brand_dna", db_brand_dna),
        "identity": body.get("identity", db_identity),
        "logo_base64": logo_base64,
        "logo_mime_type": logo_mime_type,
    }
    result = _video_agent.invoke(initial_state)

    completed_scenes = result.get("completed_scenes", [])
    generations = []
    for scene in completed_scenes:
        gen = Generation.objects.create(
            creation=creation,
            media_type="video",
            prompt=f"Scene {scene.get('scene_number', '')}",
            status="done",
            generation_params={
                "scene_number": scene.get("scene_number"),
                "type": scene.get("type", ""),
                "filtered": scene.get("filtered", False),
            },
        )
        if scene.get("video_url"):
            MediaFile.objects.create(
                generation=gen,
                url=scene["video_url"],
                file_type="video/mp4",
            )
        generations.append(gen)

    return generations, {
        "caption": result.get("caption", ""),
        "hashtags": result.get("hashtags", []),
    }


def _pipeline_edit_image(parent_generation, body: dict):
    """Edit an existing image generation. Returns (Generation, extra_dict)."""
    creation = parent_generation.creation

    # Get the current image URL from the parent's media files
    parent_media = parent_generation.media_files.first()
    img_url = body.get("img_url", parent_media.url if parent_media else "")

    result = _edit_image_agent.invoke({
        "creation_uuid": str(creation.uuid),
        "parent_uuid": str(parent_generation.uuid),
        "prompt": body.get("prompt", ""),
        "img_url": img_url,
    })

    result_url = result.get("result_url", "")

    generation = Generation.objects.create(
        creation=creation,
        parent=parent_generation,
        media_type="image",
        prompt=body.get("prompt", ""),
        status="done",
        generation_params={"edit_of": str(parent_generation.uuid)},
    )
    if result_url:
        MediaFile.objects.create(
            generation=generation,
            url=result_url,
            file_type="image/jpeg",
        )
    return generation, {}


def _pipeline_edit_copy(parent_generation, body: dict):
    """Regenerate marketing copy. Returns (Generation, extra_dict)."""
    creation = parent_generation.creation
    db_brand_dna, db_identity = _brand_context_from_creation(creation)
    creation_platforms = [p for p in creation.platforms.split(",") if p.strip()] if creation.platforms else ["instagram"]

    initial_state = {
        "creation_uuid": str(creation.uuid),
        "prompt": body.get("prompt", creation.original_prompt),
        "current_copy": body.get("current_copy", ""),
        "copy_feedback": body.get("copy_feedback", ""),
        "platforms": body.get("platforms", creation_platforms),
        "post_type": body.get("post_type", creation.post_type or "post"),
        "post_tone": body.get("post_tone", creation.post_tone or "promotional"),
        "brand_dna": body.get("brand_dna", {k: v for k, v in db_brand_dna.items() if k != "typography"}),
        "identity": body.get("identity", db_identity),
    }

    result = _copy_agent.invoke(initial_state)

    strategy_raw = result.get("strategy", "")
    if "---" in strategy_raw:
        _, copy_part = strategy_raw.split("---", 1)
        copy_part = copy_part.strip()
    else:
        copy_part = strategy_raw

    generation = Generation.objects.create(
        creation=creation,
        parent=parent_generation,
        media_type="image",
        prompt=body.get("prompt", creation.original_prompt),
        status="done",
        generation_params={"edit_type": "copy", "edit_of": str(parent_generation.uuid)},
    )
    return generation, {"copy": copy_part}


def _pipeline_edit_carousel_slide(parent_generation, body: dict):
    """Regenerate a single carousel slide with QC. Returns (Generation, extra_dict)."""
    creation = parent_generation.creation
    db_brand_dna, db_identity = _brand_context_from_creation(creation)
    logo_base64, logo_mime_type = _resolve_logo({**{"logo_url": db_identity.get("logo_url", "")}, **body})
    creation_platform = creation.platforms.split(",")[0].strip() if creation.platforms else "instagram"

    slide = body.get("slide", {})
    if not slide:
        # Rebuild slide from parent generation_params
        params = parent_generation.generation_params or {}
        slide = {
            "index": params.get("slide_index", 0),
            "headline": params.get("headline", ""),
        }

    visual_theme = body.get("visual_theme", "")
    platform = body.get("platform", creation_platform)
    brand_dna = body.get("brand_dna", db_brand_dna)
    feedback = body.get("feedback", body.get("prompt", ""))

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
            folder = f"ia_generations/{creation.uuid}/carousel"
            try:
                import uuid as _uuid_mod
                image_url = upload_image(image_b64, folder, str(_uuid_mod.uuid4()))
            except Exception as e:
                last_error = f"Cloudinary upload failed: {e}"
                image_url = ""
            break
        else:
            qc_feedback = "\n".join(issues)

    generation = Generation.objects.create(
        creation=creation,
        parent=parent_generation,
        media_type="image",
        prompt=expected_headline,
        status="done",
        generation_params={
            "slide_index": slide_index,
            "headline": expected_headline,
            "qc_passed": qc_passed,
            "qc_attempts": attempts,
            "edit_of": str(parent_generation.uuid),
        },
    )
    if image_url:
        MediaFile.objects.create(
            generation=generation,
            url=image_url,
            file_type="image/jpeg",
        )

    extra = {
        "slide": {
            "index": slide_index,
            "headline": expected_headline,
            "image_url": image_url,
            "qc_passed": qc_passed,
            "qc_attempts": attempts,
        }
    }
    if not image_url and last_error:
        extra["slide"]["error"] = last_error

    return generation, extra


_EDIT_VALID_TYPES = ["edit_image", "edit_copy", "edit_carousel_slide"]


class GenerationListView(APIView):
    """List all generations for a creation or create a new generation."""
    authentication_classes = [SIAJWTAuthentication, SIAAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Generations'],
        summary='List Generations for Creation',
        description='''
        Retrieve all AI-generated assets associated with a specific creation project.
        Includes images, videos, and copy generated during the project lifecycle.
        Assets are returned in chronological order.
        ''',
        responses={200: GenerationListSerializer(many=True)}
    )
    def get(self, request, creation_uuid):
        user = get_current_user(request)
        creation = get_object_or_404(Creation, uuid=creation_uuid)
        if not check_ownership(creation, user):
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
            
        queryset = creation.generations.all()
        serializer = GenerationListSerializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        tags=['Generations'],
        summary='Create or Edit Generation',
        description=(
            "Trigger an AI generation pipeline for an existing creation.\n\n"
            "**Create new** — omit `parent`, type is inferred from `creation.post_type`.\n"
            "**Edit existing** — send `parent` (generation UUID) to create a new version.\n\n"
            "---\n\n"
            "### Create flows\n\n"
            "**image** `{\"prompt\": \"...\"}` → `{generation, copy}`\n\n"
            "**carousel** `{\"prompt\": \"...\"}` → `{generations, caption, hashtags}`\n\n"
            "**video** `{\"prompt\": \"...\"}` → `{generations, caption, hashtags}`\n\n"
            "---\n\n"
            "### Edit flows (send `parent`)\n\n"
            "**edit_image** `{\"parent\": \"uuid\", \"prompt\": \"Make background blue\"}` → `{generation}`\n\n"
            "**edit_copy** `{\"parent\": \"uuid\", \"type\": \"edit_copy\", \"current_copy\": \"...\", \"copy_feedback\": \"...\"}` → `{generation, copy}`\n\n"
            "**edit_carousel_slide** `{\"parent\": \"uuid\", \"prompt\": \"More vibrant\"}` → `{generation, slide}`\n"
        ),
        responses={201: GenerationDetailSerializer},
        examples=[
            OpenApiExample(
                'Image Generation Request',
                value={
                    "type": "image",
                    "status": "done",
                    "prompt": "Professional athlete running at sunset",
                    "content": {
                        "url": "https://res.cloudinary.com/demo/image/upload/v1/creation/img1.jpg",
                        "width": 1024,
                        "height": 1024
                    }
                },
                request_only=True
            )
        ]
    )
    def post(self, request, creation_uuid):
        user = get_current_user(request)
        creation = get_object_or_404(Creation, uuid=creation_uuid)
        body = request.data
        parent_uuid = body.get("parent")

        try:
            # ── Edit flow: parent provided ──
            if parent_uuid:
                parent = get_object_or_404(Generation, uuid=parent_uuid, creation=creation)
                edit_type = body.get("type")
                if not edit_type:
                    params = parent.generation_params or {}
                    if "slide_index" in params:
                        edit_type = "edit_carousel_slide"
                    else:
                        edit_type = "edit_image"

                if edit_type == "edit_image":
                    generation, extra = _pipeline_edit_image(parent, body)
                elif edit_type == "edit_copy":
                    generation, extra = _pipeline_edit_copy(parent, body)
                elif edit_type == "edit_carousel_slide":
                    generation, extra = _pipeline_edit_carousel_slide(parent, body)
                else:
                    return Response(
                        {"error": f"Unknown edit type '{edit_type}'. Valid values: {_EDIT_VALID_TYPES}"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                return Response(
                    {"generation": GenerationDetailSerializer(generation).data, **extra},
                    status=status.HTTP_201_CREATED,
                )

            # ── Create flow: no parent ──
            content_type = body.get("type") or _POST_TYPE_TO_PIPELINE.get(creation.post_type)

            if not content_type:
                return Response(
                    {"error": f"Could not infer type from creation.post_type='{creation.post_type}'. Provide 'type' explicitly. Valid values: {_GENERATION_VALID_TYPES}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if content_type == "image":
                generation, extra = _pipeline_image(creation, body)
                return Response(
                    {"generation": GenerationDetailSerializer(generation).data, **extra},
                    status=status.HTTP_201_CREATED,
                )
            elif content_type == "carousel":
                generations, extra = _pipeline_carousel(creation, body)
                return Response(
                    {"generations": GenerationDetailSerializer(generations, many=True).data, **extra},
                    status=status.HTTP_201_CREATED,
                )
            elif content_type == "video":
                generations, extra = _pipeline_video(creation, body)
                return Response(
                    {"generations": GenerationDetailSerializer(generations, many=True).data, **extra},
                    status=status.HTTP_201_CREATED,
                )
            else:
                return Response(
                    {"error": f"Unknown type '{content_type}'. Valid values: {_GENERATION_VALID_TYPES}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GenerationDetailView(APIView):
    """Retrieve or delete a generation."""
    authentication_classes = [SIAJWTAuthentication, SIAAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Generations'],
        summary='Get Generation Details',
        description='Get specific generation info including content and prompt.',
        responses={200: GenerationDetailSerializer, 404: OpenApiResponse(description='Not found')}
    )
    def get(self, request, uuid):
        user = get_current_user(request)
        generation = get_object_or_404(Generation, uuid=uuid)
        if not check_ownership(generation, user):
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
            
        serializer = GenerationDetailSerializer(generation)
        return Response(serializer.data)

    @extend_schema(
        tags=['Generations'],
        summary='Update Generation',
        request=GenerationUpdateSerializer,
        responses={200: GenerationDetailSerializer}
    )
    def patch(self, request, uuid):
        user = get_current_user(request)
        generation = get_object_or_404(Generation, uuid=uuid)
        if not check_ownership(generation, user):
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        serializer = GenerationUpdateSerializer(generation, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(GenerationDetailSerializer(generation).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=['Generations'],
        summary='Delete Generation',
        responses={204: OpenApiResponse(description='Deleted successfully')}
    )
    def delete(self, request, uuid):
        user = get_current_user(request)
        generation = get_object_or_404(Generation, uuid=uuid)
        if not check_ownership(generation, user):
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        generation.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ============ Preview Endpoints ============

class PreviewListView(APIView):
    """List all previews or create a new one."""
    authentication_classes = [SIAJWTAuthentication, SIAAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Previews'],
        summary='List Previews',
        description='Retrieve a list of all preview versions available.',
        responses={200: PreviewDetailSerializer(many=True)}
    )
    def get(self, request):
        queryset = Preview.objects.all()
        serializer = PreviewDetailSerializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        tags=['Previews'],
        summary='Create Preview',
        description='''
        Create a new preview version.
        Presets are used to group specific generations together into a single "draft" or "proposal" 
        that can later be promoted to a Post.
        ''',
        request=PreviewCreateSerializer,
        responses={201: PreviewDetailSerializer},
        examples=[
            OpenApiExample(
                'Create Preview Request',
                value={
                    "version_name": "V1 - Dark Mode Style",
                    "internal_notes": "Awaiting client feedback on typography"
                },
                request_only=True
            )
        ]
    )
    def post(self, request):
        serializer = PreviewCreateSerializer(data=request.data)
        if serializer.is_valid():
            preview = serializer.save()
            return Response(PreviewDetailSerializer(preview).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PreviewDetailView(APIView):
    """Retrieve, update or delete a preview."""
    authentication_classes = [SIAJWTAuthentication, SIAAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Previews'],
        summary='Get Preview Details',
        description='Get preview composition and its items.',
        responses={200: PreviewDetailSerializer, 404: OpenApiResponse(description='Not found')}
    )
    def get(self, request, uuid):
        preview = get_object_or_404(Preview, uuid=uuid)
        serializer = PreviewDetailSerializer(preview)
        return Response(serializer.data)

    @extend_schema(
        tags=['Previews'],
        summary='Update Preview',
        request=PreviewCreateSerializer,
        responses={200: PreviewDetailSerializer}
    )
    def patch(self, request, uuid):
        preview = get_object_or_404(Preview, uuid=uuid)
        serializer = PreviewCreateSerializer(preview, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(PreviewDetailSerializer(preview).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=['Previews'],
        summary='Delete Preview',
        responses={204: OpenApiResponse(description='Deleted successfully')}
    )
    def delete(self, request, uuid):
        preview = get_object_or_404(Preview, uuid=uuid)
        preview.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PreviewItemListView(APIView):
    """Manage items within a preview."""
    authentication_classes = [SIAJWTAuthentication, SIAAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Previews'],
        summary='Add Item to Preview',
        description='Link a generation to a preview version at a specific position.',
        request=PreviewItemSerializer,
        responses={201: PreviewItemSerializer}
    )
    def post(self, request, preview_uuid):
        preview = get_object_or_404(Preview, uuid=preview_uuid)
        data = request.data.copy()
        data['preview'] = preview.uuid
        
        serializer = PreviewItemSerializer(data=data)
        if serializer.is_valid():
            item = serializer.save(preview=preview)
            return Response(PreviewItemSerializer(item).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ============ Post Endpoints ============

class PostListView(APIView):
    """List all posts or create a new post."""
    authentication_classes = [SIAJWTAuthentication, SIAAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Posts'],
        summary='List All Posts',
        description='''
        Retrieve a list of finalized posts.
        Posts are the final stage of the creation workflow, containing the approved copy 
        and scheduled publication dates.
        ''',
        parameters=[
            OpenApiParameter(name='brand_uuid', type=str, location=OpenApiParameter.QUERY, description='Filter by brand', required=False),
            OpenApiParameter(name='status', type=str, location=OpenApiParameter.QUERY, description='Filter by status (draft, scheduled, published)', required=False),
        ],
        responses={200: PostListSerializer(many=True)}
    )
    def get(self, request):
        user = get_current_user(request)
        queryset = Post.objects.all()

        if user and user.user_id != 'service':
            queryset = queryset.filter(user_id=user.user_id)

        brand_uuid = request.query_params.get('brand_uuid')
        if brand_uuid:
            queryset = queryset.filter(brand__uuid=brand_uuid)

        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        serializer = PostListSerializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        tags=['Posts'],
        summary='Create New Post',
        description='''
        Promote a preview to a finalized Post.
        Requires a link to a `brand` and a specific `preview` version.
        The `final_copy` field should contain the approved marketing text.
        ''',
        request=PostCreateSerializer,
        responses={201: PostDetailSerializer},
        examples=[
            OpenApiExample(
                'Create Post Request',
                value={
                    "brand": "a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6",
                    "preview": "e5f6g7h8-i9j0-k1l2-m3n4-o5p6q7r8s9t0",
                    "final_copy": "Unlock your potential with the new Nike Air Collection. #Nike #JustDoIt",
                    "status": "scheduled",
                    "scheduled_date": "2026-03-15T10:00:00Z",
                    "post_type": "post",
                    "platforms": "instagram,facebook,linkedin"
                },
                request_only=True
            )
        ]
    )
    def post(self, request):
        user = get_current_user(request)
        serializer = PostCreateSerializer(data=request.data)
        if serializer.is_valid():
            brand = serializer.validated_data.get('brand')
            if brand and not check_ownership(brand, user):
                return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
                
            if user:
                post = serializer.save(user_id=user.user_id)
            else:
                post = serializer.save()
                
            return Response(PostDetailSerializer(post).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PostDetailView(APIView):
    """Retrieve, update or delete a post."""
    authentication_classes = [SIAJWTAuthentication, SIAAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Posts'],
        summary='Get Post Details',
        description='Get full post details including performance metrics.',
        responses={200: PostDetailSerializer, 404: OpenApiResponse(description='Not found')}
    )
    def get(self, request, uuid):
        user = get_current_user(request)
        post = get_object_or_404(Post, uuid=uuid)
        if not check_ownership(post, user):
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
            
        serializer = PostDetailSerializer(post)
        return Response(serializer.data)

    @extend_schema(
        tags=['Posts'],
        summary='Update Post',
        request=PostUpdateSerializer,
        responses={200: PostDetailSerializer}
    )
    def patch(self, request, uuid):
        user = get_current_user(request)
        post = get_object_or_404(Post, uuid=uuid)
        if not check_ownership(post, user):
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        serializer = PostUpdateSerializer(post, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(PostDetailSerializer(post).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=['Posts'],
        summary='Delete Post',
        responses={204: OpenApiResponse(description='Deleted successfully')}
    )
    def delete(self, request, uuid):
        user = get_current_user(request)
        post = get_object_or_404(Post, uuid=uuid)
        if not check_ownership(post, user):
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        post.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PostMetricsView(APIView):
    """Update post performance metrics."""
    authentication_classes = [SIAJWTAuthentication, SIAAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Posts'],
        summary='Update Post Metrics',
        description='Update performance metrics (likes, reach, etc.) for a published post.',
        request=PostMetricsUpdateSerializer,
        responses={200: PostDetailSerializer}
    )
    def patch(self, request, uuid):
        user = get_current_user(request)
        post = get_object_or_404(Post, uuid=uuid)
        if not check_ownership(post, user):
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        serializer = PostMetricsUpdateSerializer(data=request.data)
        if serializer.is_valid():
            for field in ['likes', 'comments', 'shares', 'reach']:
                if field in serializer.validated_data:
                    setattr(post, field, serializer.validated_data[field])

            post.engagement_rate = post.calculate_engagement_rate()
            post.save()
            return Response(PostDetailSerializer(post).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ============ Platform Insight Endpoints ============

class PlatformInsightListView(APIView):
    """List all platform insights or create new ones."""
    authentication_classes = [SIAJWTAuthentication, SIAAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Platform Insights'],
        summary='List Platform Insights',
        description='''
        Retrieve time-series performance data for a specific brand across various platforms.
        This data includes daily snapshots of follower counts, impressions, and reach.
        Useful for building analytics dashboards and tracking growth trends.
        ''',
        parameters=[
            OpenApiParameter(name='brand_uuid', type=str, location=OpenApiParameter.QUERY, description='UUID of the brand', required=False),
            OpenApiParameter(name='platform', type=str, location=OpenApiParameter.QUERY, description='Filter by platform (facebook, instagram, etc.)', required=False),
            OpenApiParameter(name='date_from', type=str, location=OpenApiParameter.QUERY, description='Start date for trend data (YYYY-MM-DD)', required=False),
            OpenApiParameter(name='date_to', type=str, location=OpenApiParameter.QUERY, description='End date for trend data (YYYY-MM-DD)', required=False),
        ],
        responses={200: PlatformInsightSerializer(many=True)},
        examples=[
            OpenApiExample(
                'Insight Trend Response',
                value=[
                    {
                        "uuid": "u1v2w3x4-y5z6-a7b8-c9d0-e1f2g3h4i5j6",
                        "brand_uuid": "a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6",
                        "brand_name": "Nike",
                        "platform": "instagram",
                        "date": "2026-03-10",
                        "followers": 150200,
                        "impressions": 12000,
                        "reach": 8500,
                        "engagement_rate": 3.2,
                        "created_at": "2026-03-11T00:00:00Z"
                    }
                ],
                response_only=True
            )
        ]
    )
    def get(self, request):
        user = get_current_user(request)
        queryset = PlatformInsight.objects.all()

        if user and user.user_id != 'service':
            queryset = queryset.filter(brand__user_id=user.user_id)

        brand_uuid = request.query_params.get('brand_uuid')
        if brand_uuid:
            queryset = queryset.filter(brand__uuid=brand_uuid)

        platform = request.query_params.get('platform')
        if platform:
            queryset = queryset.filter(platform=platform)

        date_from = request.query_params.get('date_from')
        if date_from:
            queryset = queryset.filter(date__gte=date_from)

        date_to = request.query_params.get('date_to')
        if date_to:
            queryset = queryset.filter(date__lte=date_to)

        serializer = PlatformInsightSerializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        tags=['Platform Insights'],
        summary='Create Platform Insight',
        description='Record a single daily snapshot of metrics for a brand on a specific platform.',
        request=PlatformInsightCreateSerializer,
        responses={201: PlatformInsightSerializer},
        examples=[
            OpenApiExample(
                'Create Insight Request',
                value={
                    "brand": "a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6",
                    "platform": "facebook",
                    "date": "2026-03-10",
                    "followers": 85400,
                    "impressions": 5000,
                    "reach": 4200,
                    "engagement_rate": 2.1
                },
                request_only=True
            )
        ]
    )
    def post(self, request):
        user = get_current_user(request)
        serializer = PlatformInsightCreateSerializer(data=request.data)
        if serializer.is_valid():
            brand = serializer.validated_data.get('brand')
            if brand and not check_ownership(brand, user):
                return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
                
            insight = serializer.save()
            return Response(PlatformInsightSerializer(insight).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PlatformInsightBulkCreateView(APIView):
    """Bulk create platform insights."""
    authentication_classes = [SIAJWTAuthentication, SIAAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Platform Insights'],
        summary='Bulk Create Insights',
        description='''
        Efficiently upload multiple metric snapshots in a single request. 
        Highly recommended for syncing historical data or daily updates for multiple dates/platforms.
        ''',
        request=PlatformInsightBulkCreateSerializer,
        responses={201: PlatformInsightSerializer(many=True)}
    )
    def post(self, request):
        serializer = PlatformInsightBulkCreateSerializer(data=request.data)
        if serializer.is_valid():
            result = serializer.save()
            return Response(
                PlatformInsightSerializer(result['insights'], many=True).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PlatformInsightDetailView(APIView):
    """Retrieve or delete a platform insight."""
    authentication_classes = [SIAJWTAuthentication, SIAAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Platform Insights'],
        summary='Get Platform Insight Details',
        responses={200: PlatformInsightSerializer, 404: OpenApiResponse(description='Not found')}
    )
    def get(self, request, uuid):
        user = get_current_user(request)
        insight = get_object_or_404(PlatformInsight, uuid=uuid)
        if not check_ownership(insight.brand, user):
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
            
        serializer = PlatformInsightSerializer(insight)
        return Response(serializer.data)

    @extend_schema(
        tags=['Platform Insights'],
        summary='Delete Platform Insight',
        responses={204: OpenApiResponse(description='Deleted successfully')}
    )
    def delete(self, request, uuid):
        user = get_current_user(request)
        insight = get_object_or_404(PlatformInsight, uuid=uuid)
        if not check_ownership(insight.brand, user):
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        insight.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
