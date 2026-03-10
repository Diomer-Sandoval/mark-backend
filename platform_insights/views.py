from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse, inline_serializer
from creation_studio.models.core import Brand
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
