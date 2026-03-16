from .models import Post, PlatformInsight
from brand_dna_extractor.models import Brand
from .serializers import (
    PostListSerializer, PostDetailSerializer,
    PostCreateSerializer, PostUpdateSerializer,
    PostMetricsUpdateSerializer,
    PlatformInsightSerializer, PlatformInsightCreateSerializer,
    PlatformInsightBulkCreateSerializer
)
from authentication import (
    SIAJWTAuthentication, SIAAPIKeyAuthentication,
    get_current_user
)
from config.utils import check_ownership
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse, OpenApiExample, inline_serializer
from django.shortcuts import get_object_or_404
from .services.meta_client import MetaInsightService
import logging

logger = logging.getLogger(__name__)

class SyncInsightsView(APIView):
    """
    Endpoint to trigger syncing insights for a specific brand.
    Expected payload: {"brand_id": "uuid-of-the-brand"}
    """
    
    @extend_schema(
        tags=['Platform Insights'],
        summary='Sync Meta Insights and Posts',
        description='Fetches the latest 28 days of insights (reach, impressions, followers) and the latest organic posts for a specific brand from Meta Graph API (Facebook and Instagram). Inserts/Updates the records automatically matching the linked tenant and user.',
        request=inline_serializer(
            name='SyncInsightsRequest',
            fields={
                'brand_id': serializers.UUIDField(help_text="The internal UUID of the existing Brand.")
            }
        ),
        responses={
            200: OpenApiResponse(
                description='Successful Sync',
                response=inline_serializer(
                    name='SyncInsightsSuccessResponse',
                    fields={
                        'message': serializers.CharField(),
                        'instagram_records_synced': serializers.IntegerField(),
                        'facebook_records_synced': serializers.IntegerField(),
                        'external_posts_synced_or_updated': serializers.IntegerField(),
                    }
                ),
                examples=[
                    OpenApiExample(
                        'Success Example',
                        value={
                            "message": "Successfully processed insights and posts for brand: Cloudinary",
                            "instagram_records_synced": 28,
                            "facebook_records_synced": 28,
                            "external_posts_synced_or_updated": 15
                        }
                    )
                ]
            ),
            400: OpenApiResponse(
                description='Bad Request',
                response=inline_serializer(
                    name='SyncInsightsErrorResponse',
                    fields={
                        'error': serializers.CharField()
                    }
                )
            ),
            500: OpenApiResponse(description='Internal Server Error')
        }
    )
    def post(self, request, *args, **kwargs):
        brand_id = request.data.get('brand_id')
        
        if not brand_id:
            return Response(
                {"error": "brand_id is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        brand = get_object_or_404(Brand, uuid=brand_id, is_active=True)
        
        service = MetaInsightService()
        try:
            ig_count, fb_count = service.sync_insights_for_brand(brand, days=30)
            posts_count = service.sync_external_posts_for_brand(brand)
            return Response(
                {
                    "message": f"Successfully processed insights and posts for brand: {brand.name}",
                    "instagram_records_synced": ig_count,
                    "facebook_records_synced": fb_count,
                    "external_posts_synced_or_updated": posts_count
                }, 
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"Error syncing insights for {brand_id}: {str(e)}")
            return Response(
                {"error": f"Failed to sync insights: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

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
        queryset = Post.objects.select_related('brand', 'preview').all()

        if user and user.user_id != 'service':
            queryset = queryset.filter(brand__user_id=user.user_id)

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
        queryset = PlatformInsight.objects.select_related('brand').all()

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
