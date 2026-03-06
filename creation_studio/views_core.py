"""
Core API Views for Creation Studio.

Provides REST endpoints for:
- Brands and Brand DNA
- Creations and Generations
- Posts and Platform Insights
- Media Files

All endpoints require authentication via SIA Solutions JWT or API Key.
Data is automatically filtered to show only the current user's records.
"""

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse, OpenApiExample

from .models_core import (
    Brand, BrandDNA, Creation, Generation,
    Post, PlatformInsight, MediaFile
)
from .authentication import (
    SIAJWTAuthentication, SIAAPIKeyAuthentication,
    get_current_user, can_access_mark
)
from .serializers_core import (
    # Brand
    BrandListSerializer, BrandDetailSerializer,
    BrandCreateSerializer, BrandUpdateSerializer,
    # BrandDNA
    BrandDNASerializer, BrandDNACreateSerializer,
    # Creation
    CreationListSerializer, CreationDetailSerializer,
    CreationCreateSerializer, CreationUpdateSerializer,
    CreationSearchRequestSerializer,
    # Generation
    GenerationListSerializer, GenerationDetailSerializer,
    GenerationCreateSerializer, GenerationUpdateSerializer,
    # Post
    PostListSerializer, PostDetailSerializer,
    PostCreateSerializer, PostUpdateSerializer,
    PostMetricsUpdateSerializer,
    # Platform Insight
    PlatformInsightSerializer, PlatformInsightCreateSerializer,
    PlatformInsightBulkCreateSerializer,
    # Media File
    MediaFileSerializer, MediaFileCreateSerializer,
)


def check_ownership(obj, user):
    """Check if user owns this object or is super admin."""
    if not user:
        return False
    if user.role == 'super_admin':
        return True
    if hasattr(obj, 'user_id') and obj.user_id == user.user_id:
        return True
    if hasattr(obj, 'tenant_id') and user.tenant_id and obj.tenant_id == user.tenant_id:
        return True
    return False


# ============ Brand Endpoints ============

class BrandListView(APIView):
    """List all brands or create a new brand."""
    authentication_classes = [SIAJWTAuthentication, SIAAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Brands'],
        summary='List All Brands',
        description='Get a list of all brands for the authenticated user with optional filtering.',
        parameters=[
            OpenApiParameter(name='is_active', type=bool, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name='industry', type=str, location=OpenApiParameter.QUERY, required=False),
        ],
        responses={200: BrandListSerializer(many=True)},
        examples=[
            OpenApiExample(
                'Success Response',
                value=[
                    {
                        "uuid": "a1b2c3d4e5f6g7h8i",
                        "name": "Apple",
                        "slug": "apple",
                        "industry": "Technology",
                        "is_active": True,
                        "dna_uuid": "b2c3d4e5f6g7h8i9j",
                        "logo_url": "https://example.com/apple-logo.png",
                        "created_at": "2026-03-06T10:00:00Z"
                    }
                ],
                response_only=True,
                status_codes=['200']
            )
        ]
    )
    def get(self, request):
        user = get_current_user(request)
        
        # Filter by current user and tenant
        queryset = Brand.objects.all()
        if user and user.user_id != 'service':
            queryset = queryset.filter(user_id=user.user_id)
            if user.tenant_id:
                queryset = queryset.filter(tenant_id=user.tenant_id)
        
        # Filter by is_active
        is_active = request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        # Filter by industry
        industry = request.query_params.get('industry')
        if industry:
            queryset = queryset.filter(industry__icontains=industry)
        
        serializer = BrandListSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        tags=['Brands'],
        summary='Create New Brand',
        description='Create a new brand with optional BrandDNA. Automatically associated with the authenticated user.',
        request=BrandCreateSerializer,
        responses={201: BrandDetailSerializer},
        examples=[
            OpenApiExample(
                'Create Request',
                value={
                    "name": "Nike",
                    "slug": "nike",
                    "industry": "Fashion",
                    "page_url": "https://nike.com",
                    "logo_url": "https://nike.com/logo.png",
                    "dna_data": {
                        "primary_color": "#111111",
                        "secondary_color": "#FFFFFF",
                        "voice_tone": "Bold, inspirational"
                    }
                },
                request_only=True
            ),
            OpenApiExample(
                'Created Response',
                value={
                    "uuid": "c3d4e5f6g7h8i9j0k",
                    "name": "Nike",
                    "slug": "nike",
                    "page_url": "https://nike.com",
                    "logo_url": "https://nike.com/logo.png",
                    "is_active": True,
                    "industry": "Fashion",
                    "user_id": "550e8400-e29b-41d4-a716-446655440000",
                    "tenant_id": "660e8400-e29b-41d4-a716-446655440000",
                    "dna": {
                        "uuid": "d4e5f6g7h8i9j0k1l",
                        "primary_color": "#111111",
                        "secondary_color": "#FFFFFF",
                        "voice_tone": "Bold, inspirational"
                    },
                    "created_at": "2026-03-06T10:30:00Z",
                    "updated_at": "2026-03-06T10:30:00Z"
                },
                response_only=True,
                status_codes=['201']
            )
        ]
    )
    def post(self, request):
        user = get_current_user(request)
        
        serializer = BrandCreateSerializer(data=request.data)
        if serializer.is_valid():
            brand = serializer.save()
            
            # Associate with current user and tenant
            if user:
                brand.user_id = user.user_id
                brand.tenant_id = user.tenant_id
                brand.save()
            
            return Response(
                BrandDetailSerializer(brand).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BrandDetailView(APIView):
    """Retrieve, update or delete a brand."""
    authentication_classes = [SIAJWTAuthentication, SIAAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]
    
    def _check_ownership(self, brand, user):
        """Check if user owns this brand or is super admin."""
        if user.role == 'super_admin':
            return True
        if brand.user_id == user.user_id:
            return True
        if user.tenant_id and brand.tenant_id == user.tenant_id:
            return True
        return False
    
    @extend_schema(
        tags=['Brands'],
        summary='Get Brand Details',
        description='Get detailed information about a specific brand. Only accessible to the owner.',
        responses={200: BrandDetailSerializer, 404: OpenApiResponse(description='Brand not found')}
    )
    def get(self, request, uuid):
        user = get_current_user(request)
        brand = get_object_or_404(Brand, uuid=uuid)
        
        if not self._check_ownership(brand, user):
            return Response(
                {"error": "You do not have permission to view this brand."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = BrandDetailSerializer(brand)
        return Response(serializer.data)
    
    @extend_schema(
        tags=['Brands'],
        summary='Update Brand',
        description='Update brand metadata',
        request=BrandUpdateSerializer,
        responses={200: BrandDetailSerializer}
    )
    def patch(self, request, uuid):
        user = get_current_user(request)
        brand = get_object_or_404(Brand, uuid=uuid)
        
        if not self._check_ownership(brand, user):
            return Response(
                {"error": "You do not have permission to update this brand."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = BrandUpdateSerializer(brand, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(BrandDetailSerializer(brand).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        tags=['Brands'],
        summary='Delete Brand',
        description='Delete a brand and all associated data',
        responses={204: OpenApiResponse(description='Deleted successfully')}
    )
    def delete(self, request, uuid):
        user = get_current_user(request)
        brand = get_object_or_404(Brand, uuid=uuid)
        
        if not self._check_ownership(brand, user):
            return Response(
                {"error": "You do not have permission to delete this brand."},
                status=status.HTTP_403_FORBIDDEN
            )
        
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
        description='Get all brand DNA records',
        responses={200: BrandDNASerializer(many=True)}
    )
    def get(self, request):
        queryset = BrandDNA.objects.all()
        serializer = BrandDNASerializer(queryset, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        tags=['Brand DNA'],
        summary='Create Brand DNA',
        description='Create a new Brand DNA record',
        request=BrandDNACreateSerializer,
        responses={201: BrandDNASerializer}
    )
    def post(self, request):
        serializer = BrandDNACreateSerializer(data=request.data)
        if serializer.is_valid():
            dna = serializer.save()
            return Response(
                BrandDNASerializer(dna).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BrandDNADetailView(APIView):
    """Retrieve, update or delete a Brand DNA record."""
    authentication_classes = [SIAJWTAuthentication, SIAAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Brand DNA'],
        summary='Get Brand DNA',
        description='Get Brand DNA details',
        responses={200: BrandDNASerializer, 404: OpenApiResponse(description='Not found')}
    )
    def get(self, request, uuid):
        dna = get_object_or_404(BrandDNA, uuid=uuid)
        serializer = BrandDNASerializer(dna)
        return Response(serializer.data)
    
    @extend_schema(
        tags=['Brand DNA'],
        summary='Update Brand DNA',
        description='Update Brand DNA data',
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
        description='Delete Brand DNA record',
        responses={204: OpenApiResponse(description='Deleted')}
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
        description='Get Brand DNA associated with a specific brand',
        responses={200: BrandDNASerializer, 404: OpenApiResponse(description='Not found')}
    )
    def get(self, request, brand_uuid):
        brand = get_object_or_404(Brand, uuid=brand_uuid)
        if not brand.dna:
            return Response(
                {"error": "No DNA found for this brand"},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = BrandDNASerializer(brand.dna)
        return Response(serializer.data)
    
    @extend_schema(
        tags=['Brand DNA'],
        summary='Update Brand DNA by Brand',
        description='Update Brand DNA for a specific brand',
        request=BrandDNACreateSerializer,
        responses={200: BrandDNASerializer}
    )
    def patch(self, request, brand_uuid):
        brand = get_object_or_404(Brand, uuid=brand_uuid)
        if not brand.dna:
            return Response(
                {"error": "No DNA found for this brand"},
                status=status.HTTP_404_NOT_FOUND
            )
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
        description='Get a list of creation projects for the authenticated user with optional filtering',
        parameters=[
            OpenApiParameter(name='brand_uuid', type=str, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name='status', type=str, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name='post_type', type=str, location=OpenApiParameter.QUERY, required=False),
        ],
        responses={200: CreationListSerializer(many=True)},
        examples=[
            OpenApiExample(
                'Success Response',
                value=[
                    {
                        "uuid": "x1y2z3a4b5c6d7e8f",
                        "brand_uuid": "a1b2c3d4e5f6g7h8i",
                        "brand_name": "Apple",
                        "title": "iPhone 16 Launch Campaign",
                        "post_type": "carousel",
                        "status": "done",
                        "platforms": "instagram,linkedin",
                        "generation_count": 3,
                        "created_at": "2026-03-06T11:00:00Z",
                        "updated_at": "2026-03-06T14:30:00Z"
                    }
                ],
                response_only=True,
                status_codes=['200']
            )
        ]
    )
    def get(self, request):
        user = get_current_user(request)
        queryset = Creation.objects.all()
        
        # Filter by current user
        if user and user.user_id != 'service':
            queryset = queryset.filter(user_id=user.user_id)
        
        # Filter by brand
        brand_uuid = request.query_params.get('brand_uuid')
        if brand_uuid:
            queryset = queryset.filter(brand__uuid=brand_uuid)
        
        # Filter by status
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by post_type
        post_type = request.query_params.get('post_type')
        if post_type:
            queryset = queryset.filter(post_type=post_type)
        
        serializer = CreationListSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        tags=['Creations'],
        summary='Create New Creation',
        description='Create a new creation project. Automatically associated with the authenticated user.',
        request=CreationCreateSerializer,
        responses={201: CreationDetailSerializer},
        examples=[
            OpenApiExample(
                'Create Request',
                value={
                    "brand": "a1b2c3d4e5f6g7h8i",
                    "title": "Summer Sale Campaign 2026",
                    "post_type": "carousel",
                    "status": "pending",
                    "platforms": "instagram,tiktok",
                    "post_tone": "promotional",
                    "original_prompt": "Create a vibrant carousel showcasing our summer collection"
                },
                request_only=True
            )
        ]
    )
    def post(self, request):
        user = get_current_user(request)
        
        serializer = CreationCreateSerializer(data=request.data)
        if serializer.is_valid():
            creation = serializer.save()
            
            # Associate with current user
            if user:
                creation.user_id = user.user_id
                creation.save()
            
            return Response(
                CreationDetailSerializer(creation).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CreationDetailView(APIView):
    """Retrieve, update or delete a creation project."""
    authentication_classes = [SIAJWTAuthentication, SIAAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Creations'],
        summary='Get Creation Details',
        description='Get full details of a specific creation project',
        responses={200: CreationDetailSerializer, 404: OpenApiResponse(description='Not found')}
    )
    def get(self, request, uuid):
        creation = get_object_or_404(Creation, uuid=uuid)
        serializer = CreationDetailSerializer(creation)
        return Response(serializer.data)
    
    @extend_schema(
        tags=['Creations'],
        summary='Update Creation',
        description='Update creation metadata or status',
        request=CreationUpdateSerializer,
        responses={200: CreationDetailSerializer}
    )
    def patch(self, request, uuid):
        creation = get_object_or_404(Creation, uuid=uuid)
        serializer = CreationUpdateSerializer(creation, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(CreationDetailSerializer(creation).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        tags=['Creations'],
        summary='Delete Creation',
        description='Delete a creation project and all associated data',
        responses={204: OpenApiResponse(description='Deleted')}
    )
    def delete(self, request, uuid):
        creation = get_object_or_404(Creation, uuid=uuid)
        creation.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ============ Generation Endpoints ============

class GenerationListView(APIView):
    """List all generations for a creation or create a new generation."""
    authentication_classes = [SIAJWTAuthentication, SIAAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Generations'],
        summary='List Generations for Creation',
        description='Get all AI-generated assets for a specific creation project',
        responses={200: GenerationListSerializer(many=True)}
    )
    def get(self, request, creation_uuid):
        creation = get_object_or_404(Creation, uuid=creation_uuid)
        queryset = creation.generations.all()
        serializer = GenerationListSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        tags=['Generations'],
        summary='Create New Generation',
        description='Trigger a new AI visual generation. Use parent_uuid for editing an existing asset.',
        request=GenerationCreateSerializer,
        responses={201: GenerationDetailSerializer}
    )
    def post(self, request, creation_uuid):
        creation = get_object_or_404(Creation, uuid=creation_uuid)
        data = request.data.copy()
        data['creation'] = creation.uuid
        
        serializer = GenerationCreateSerializer(data=data)
        if serializer.is_valid():
            generation = serializer.save()
            return Response(
                GenerationDetailSerializer(generation).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GenerationDetailView(APIView):
    """Retrieve or delete a generation."""
    authentication_classes = [SIAJWTAuthentication, SIAAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Generations'],
        summary='Get Generation Details',
        description='Get details of a specific generation',
        responses={200: GenerationDetailSerializer, 404: OpenApiResponse(description='Not found')}
    )
    def get(self, request, uuid):
        generation = get_object_or_404(Generation, uuid=uuid)
        serializer = GenerationDetailSerializer(generation)
        return Response(serializer.data)
    
    @extend_schema(
        tags=['Generations'],
        summary='Update Generation',
        description='Update generation status or metadata',
        request=GenerationUpdateSerializer,
        responses={200: GenerationDetailSerializer}
    )
    def patch(self, request, uuid):
        generation = get_object_or_404(Generation, uuid=uuid)
        serializer = GenerationUpdateSerializer(generation, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(GenerationDetailSerializer(generation).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        tags=['Generations'],
        summary='Delete Generation',
        description='Delete a generation record',
        responses={204: OpenApiResponse(description='Deleted')}
    )
    def delete(self, request, uuid):
        generation = get_object_or_404(Generation, uuid=uuid)
        generation.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ============ Post Endpoints ============

class PostListView(APIView):
    """List all posts or create a new post."""
    authentication_classes = [SIAJWTAuthentication, SIAAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Posts'],
        summary='List All Posts',
        description='Get all finalized posts for the authenticated user. Filterable by brand_uuid.',
        parameters=[
            OpenApiParameter(name='brand_uuid', type=str, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name='status', type=str, location=OpenApiParameter.QUERY, required=False),
        ],
        responses={200: PostListSerializer(many=True)},
        examples=[
            OpenApiExample(
                'Success Response',
                value=[
                    {
                        "uuid": "p9o8n7m6l5k4j3i2h",
                        "brand_uuid": "a1b2c3d4e5f6g7h8i",
                        "creation_uuid": "x1y2z3a4b5c6d7e8f",
                        "status": "published",
                        "scheduled_date": "2026-03-10T09:00:00Z",
                        "post_type": "carousel",
                        "platforms": "instagram,linkedin",
                        "created_at": "2026-03-06T15:00:00Z"
                    }
                ],
                response_only=True,
                status_codes=['200']
            )
        ]
    )
    def get(self, request):
        user = get_current_user(request)
        queryset = Post.objects.all()
        
        # Filter by current user
        if user and user.user_id != 'service':
            queryset = queryset.filter(user_id=user.user_id)
        
        # Filter by brand
        brand_uuid = request.query_params.get('brand_uuid')
        if brand_uuid:
            queryset = queryset.filter(brand__uuid=brand_uuid)
        
        # Filter by status
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        serializer = PostListSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        tags=['Posts'],
        summary='Create New Post',
        description='Promote a generation into a post. Associated with authenticated user.',
        request=PostCreateSerializer,
        responses={201: PostDetailSerializer},
        examples=[
            OpenApiExample(
                'Create Request',
                value={
                    "brand": "a1b2c3d4e5f6g7h8i",
                    "creation": "x1y2z3a4b5c6d7e8f",
                    "copy": "The perfect balance of heat and sweet. 🔥🍫\n\n#chocolate #spicy #foodie",
                    "status": "scheduled",
                    "scheduled_date": "2026-03-10T14:30:00Z",
                    "post_type": "post",
                    "platforms": "instagram,facebook"
                },
                request_only=True
            ),
            OpenApiExample(
                'Created Response',
                value={
                    "uuid": "p9o8n7m6l5k4j3i2h",
                    "brand_uuid": "a1b2c3d4e5f6g7h8i",
                    "creation_uuid": "x1y2z3a4b5c6d7e8f",
                    "copy": "The perfect balance of heat and sweet. 🔥🍫\n\n#chocolate #spicy #foodie",
                    "status": "scheduled",
                    "scheduled_date": "2026-03-10T14:30:00Z",
                    "executed_at": None,
                    "post_type": "post",
                    "platforms": "instagram,facebook",
                    "likes": 0,
                    "comments": 0,
                    "shares": 0,
                    "reach": 0,
                    "engagement_rate": 0.0,
                    "created_at": "2026-03-06T15:30:00Z",
                    "updated_at": "2026-03-06T15:30:00Z"
                },
                response_only=True,
                status_codes=['201']
            )
        ]
    )
    def post(self, request):
        user = get_current_user(request)
        
        serializer = PostCreateSerializer(data=request.data)
        if serializer.is_valid():
            post = serializer.save()
            
            # Associate with current user
            if user:
                post.user_id = user.user_id
                post.save()
            
            return Response(
                PostDetailSerializer(post).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PostDetailView(APIView):
    """Retrieve, update or delete a post."""
    authentication_classes = [SIAJWTAuthentication, SIAAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Posts'],
        summary='Get Post Details',
        description='Get a post with its full copy and performance metrics',
        responses={200: PostDetailSerializer, 404: OpenApiResponse(description='Not found')}
    )
    def get(self, request, uuid):
        post = get_object_or_404(Post, uuid=uuid)
        serializer = PostDetailSerializer(post)
        return Response(serializer.data)
    
    @extend_schema(
        tags=['Posts'],
        summary='Update Post',
        description='Update post content or metrics',
        request=PostUpdateSerializer,
        responses={200: PostDetailSerializer}
    )
    def patch(self, request, uuid):
        post = get_object_or_404(Post, uuid=uuid)
        serializer = PostUpdateSerializer(post, data=request.data, partial=True)
        if serializer.is_valid():
            # Recalculate engagement rate if metrics changed
            likes = serializer.validated_data.get('likes', post.likes)
            comments = serializer.validated_data.get('comments', post.comments)
            shares = serializer.validated_data.get('shares', post.shares)
            reach = serializer.validated_data.get('reach', post.reach)
            
            if reach > 0:
                total_engagement = likes + comments + shares
                post.engagement_rate = (total_engagement / reach) * 100
            
            serializer.save()
            return Response(PostDetailSerializer(post).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        tags=['Posts'],
        summary='Delete Post',
        description='Delete a post record',
        responses={204: OpenApiResponse(description='Deleted')}
    )
    def delete(self, request, uuid):
        post = get_object_or_404(Post, uuid=uuid)
        post.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PostMetricsView(APIView):
    """Update post performance metrics."""
    authentication_classes = [SIAJWTAuthentication, SIAAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Posts'],
        summary='Update Post Metrics',
        description='Update engagement metrics for a post',
        request=PostMetricsUpdateSerializer,
        responses={200: PostDetailSerializer}
    )
    def patch(self, request, uuid):
        post = get_object_or_404(Post, uuid=uuid)
        serializer = PostMetricsUpdateSerializer(data=request.data)
        if serializer.is_valid():
            # Update fields
            for field in ['likes', 'comments', 'shares', 'reach', 'engagement_rate']:
                if field in serializer.validated_data:
                    setattr(post, field, serializer.validated_data[field])
            
            # Recalculate engagement rate if not provided
            if 'engagement_rate' not in serializer.validated_data and post.reach > 0:
                total_engagement = post.likes + post.comments + post.shares
                post.engagement_rate = (total_engagement / post.reach) * 100
            
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
        description='Get time-series data for brand growth across platforms',
        parameters=[
            OpenApiParameter(name='brand_uuid', type=str, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name='platform', type=str, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name='date_from', type=str, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name='date_to', type=str, location=OpenApiParameter.QUERY, required=False),
        ],
        responses={200: PlatformInsightSerializer(many=True)}
    )
    def get(self, request):
        queryset = PlatformInsight.objects.all()
        
        # Filter by brand
        brand_uuid = request.query_params.get('brand_uuid')
        if brand_uuid:
            queryset = queryset.filter(brand__uuid=brand_uuid)
        
        # Filter by platform
        platform = request.query_params.get('platform')
        if platform:
            queryset = queryset.filter(platform=platform)
        
        # Filter by date range
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
        description='Record daily platform metrics',
        request=PlatformInsightCreateSerializer,
        responses={201: PlatformInsightSerializer}
    )
    def post(self, request):
        serializer = PlatformInsightCreateSerializer(data=request.data)
        if serializer.is_valid():
            insight = serializer.save()
            return Response(
                PlatformInsightSerializer(insight).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PlatformInsightBulkCreateView(APIView):
    """Bulk create platform insights."""
    authentication_classes = [SIAJWTAuthentication, SIAAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Platform Insights'],
        summary='Bulk Create Insights',
        description='Create multiple platform insights at once',
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
        summary='Get Platform Insight',
        description='Get specific platform insight record',
        responses={200: PlatformInsightSerializer, 404: OpenApiResponse(description='Not found')}
    )
    def get(self, request, uuid):
        insight = get_object_or_404(PlatformInsight, uuid=uuid)
        serializer = PlatformInsightSerializer(insight)
        return Response(serializer.data)
    
    @extend_schema(
        tags=['Platform Insights'],
        summary='Delete Platform Insight',
        description='Delete a platform insight record',
        responses={204: OpenApiResponse(description='Deleted')}
    )
    def delete(self, request, uuid):
        insight = get_object_or_404(PlatformInsight, uuid=uuid)
        insight.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ============ Media File Endpoints ============

class MediaFileListView(APIView):
    """List all media files for a generation."""
    authentication_classes = [SIAJWTAuthentication, SIAAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Media Files'],
        summary='List Media Files',
        description='Get all media files for a generation',
        responses={200: MediaFileSerializer(many=True)}
    )
    def get(self, request, generation_uuid):
        generation = get_object_or_404(Generation, uuid=generation_uuid)
        queryset = generation.media_files.all()
        serializer = MediaFileSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        tags=['Media Files'],
        summary='Create Media File',
        description='Add a media file reference to a generation',
        request=MediaFileCreateSerializer,
        responses={201: MediaFileSerializer}
    )
    def post(self, request, generation_uuid):
        generation = get_object_or_404(Generation, uuid=generation_uuid)
        data = request.data.copy()
        data['generation'] = generation.uuid
        
        serializer = MediaFileCreateSerializer(data=data)
        if serializer.is_valid():
            media_file = serializer.save()
            return Response(
                MediaFileSerializer(media_file).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MediaFileDetailView(APIView):
    """Retrieve or delete a media file."""
    authentication_classes = [SIAJWTAuthentication, SIAAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Media Files'],
        summary='Get Media File',
        description='Get media file details',
        responses={200: MediaFileSerializer, 404: OpenApiResponse(description='Not found')}
    )
    def get(self, request, uuid):
        media_file = get_object_or_404(MediaFile, uuid=uuid)
        serializer = MediaFileSerializer(media_file)
        return Response(serializer.data)
    
    @extend_schema(
        tags=['Media Files'],
        summary='Delete Media File',
        description='Delete a media file reference',
        responses={204: OpenApiResponse(description='Deleted')}
    )
    def delete(self, request, uuid):
        media_file = get_object_or_404(MediaFile, uuid=uuid)
        media_file.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
