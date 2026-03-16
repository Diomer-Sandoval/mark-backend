"""
API Views for Template Vector Database.

Provides REST endpoints for:
- Template search (semantic similarity)
- Template retrieval
- Template listing
- Health checks
- Admin operations (ingestion)
"""

import os
import json
from datetime import datetime
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from django.db import connection
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, OpenApiResponse

from .models import TemplateDocument
from .services.search import TemplateSearchService
from .services.embedding import TemplateEmbeddingService
from .serializers import (
    TemplateDocumentSerializer,
    TemplateListSerializer,
    TemplateSearchResultSerializer,
    TemplateSearchRequestSerializer,
    TemplateIngestRequestSerializer,
    HealthCheckSerializer
)


class HealthCheckView(APIView):
    """Health check endpoint - public access."""
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Health'],
        summary='Health Check',
        description='Check system health and database connectivity',
        responses={200: HealthCheckSerializer}
    )
    def get(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            db_status = "connected"
        except Exception as e:
            db_status = f"error: {str(e)}"

        try:
            template_count = TemplateDocument.objects.count()
        except Exception:
            template_count = 0

        data = {
            "status": "healthy" if db_status == "connected" else "unhealthy",
            "database": db_status,
            "total_templates": template_count,
            "version": "1.0.0",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        return Response(data, status=status.HTTP_200_OK)


class TemplateListView(APIView):
    """List all templates - public access."""
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Templates'],
        summary='List All Templates',
        description='Get a paginated list of all templates with optional filters',
        parameters=[
            OpenApiParameter(name='page', type=int, location=OpenApiParameter.QUERY, description='Page number (default: 1)', default=1),
            OpenApiParameter(name='page_size', type=int, location=OpenApiParameter.QUERY, description='Items per page (default: 20, max: 100)', default=20),
            OpenApiParameter(name='template_type', type=str, location=OpenApiParameter.QUERY, description='Filter by template type (e.g., instagram, facebook)', required=False),
            OpenApiParameter(name='design_style', type=str, location=OpenApiParameter.QUERY, description='Filter by design style (e.g., minimalist, professional)', required=False),
        ],
        responses={200: TemplateListSerializer(many=True)}
    )
    def get(self, request):
        page = int(request.query_params.get('page', 1))
        page_size = min(int(request.query_params.get('page_size', 20)), 100)
        template_type = request.query_params.get('template_type')
        design_style = request.query_params.get('design_style')

        queryset = TemplateDocument.objects.all().order_by('id')

        if template_type:
            queryset = queryset.filter(metadata__template_type=template_type)
        if design_style:
            queryset = queryset.filter(metadata__design_style=design_style)

        total_count = queryset.count()
        start = (page - 1) * page_size
        end = start + page_size
        templates = queryset[start:end]

        serializer = TemplateListSerializer(templates, many=True)

        base_url = request.build_absolute_uri('?').split('?')[0]
        next_url = None
        previous_url = None

        if end < total_count:
            next_url = f"{base_url}?page={page + 1}&page_size={page_size}"
            if template_type:
                next_url += f"&template_type={template_type}"
            if design_style:
                next_url += f"&design_style={design_style}"

        if page > 1:
            previous_url = f"{base_url}?page={page - 1}&page_size={page_size}"
            if template_type:
                previous_url += f"&template_type={template_type}"
            if design_style:
                previous_url += f"&design_style={design_style}"

        return Response({
            "count": total_count,
            "next": next_url,
            "previous": previous_url,
            "results": serializer.data
        })


class TemplateDetailView(APIView):
    """Get template details - public access."""
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Templates'],
        summary='Get Template Details',
        description='Get detailed information about a specific template by ID',
        parameters=[OpenApiParameter(name='template_id', type=str, location=OpenApiParameter.PATH, description='Template ID from metadata')],
        responses={200: TemplateDocumentSerializer, 404: OpenApiResponse(description='Template not found')}
    )
    def get(self, request, template_id):
        template = get_object_or_404(TemplateDocument, metadata__id=template_id)
        serializer = TemplateDocumentSerializer(template)
        return Response(serializer.data)


class TemplateSearchView(APIView):
    """Search templates - public access."""
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Search'],
        summary='Search Templates (Semantic)',
        description='Perform semantic similarity search to find templates matching a natural language description. This endpoint uses OpenAI embeddings and cosine similarity to find the most relevant templates. Example queries: bold tech product launch with dark background, elegant fashion post for beauty brand, minimalist consulting firm announcement',
        request=TemplateSearchRequestSerializer,
        responses={200: TemplateSearchResultSerializer(many=True), 400: OpenApiResponse(description='Invalid request'), 503: OpenApiResponse(description='OpenAI API not configured')}
    )
    def post(self, request):
        request_serializer = TemplateSearchRequestSerializer(data=request.data)
        if not request_serializer.is_valid():
            return Response(
                {"error": "Invalid request", "details": request_serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        query = request_serializer.validated_data['query']
        match_count = request_serializer.validated_data.get('match_count', 50)
        filters = request_serializer.validated_data.get('filters', {})

        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            return Response(
                {"error": "OpenAI API key not configured"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        try:
            embedding_service = TemplateEmbeddingService(api_key=api_key)
            query_embedding = embedding_service.embed_text(query)

            search_service = TemplateSearchService()
            results = search_service.match_documents(query_embedding, match_count=match_count * 2)

            filtered_results = []
            for doc, similarity in results:
                metadata = doc.metadata

                if filters.get('template_type') and metadata.get('template_type') != filters['template_type']:
                    continue
                if filters.get('design_style') and metadata.get('design_style') != filters['design_style']:
                    continue
                if filters.get('industry') and filters['industry'] not in metadata.get('industry_fit', []):
                    continue

                filtered_results.append({'template': doc, 'similarity': similarity})

                if len(filtered_results) >= match_count:
                    break

            serializer = TemplateSearchResultSerializer(filtered_results, many=True)

            return Response({
                "query": query,
                "total_results": len(filtered_results),
                "filters_applied": filters if filters else None,
                "results": serializer.data
            })

        except Exception as e:
            return Response(
                {"error": "Search failed", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TemplateStatsView(APIView):
    """Template statistics - public access."""
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Templates'],
        summary='Template Statistics',
        description='Get statistics about templates (count by type, style, industry)',
        responses={200: OpenApiResponse(description='Statistics data')}
    )
    def get(self, request):
        templates = TemplateDocument.objects.all()
        total = templates.count()

        by_type = {}
        by_style = {}
        by_industry = {}

        for template in templates:
            metadata = template.metadata

            t_type = metadata.get('template_type', 'unknown')
            by_type[t_type] = by_type.get(t_type, 0) + 1

            style = metadata.get('design_style', 'unknown')
            if style:
                by_style[style] = by_style.get(style, 0) + 1

            for industry in metadata.get('industry_fit', []):
                by_industry[industry] = by_industry.get(industry, 0) + 1

        return Response({
            "total_templates": total,
            "by_type": by_type,
            "by_style": by_style,
            "by_industry": by_industry
        })


class TemplateIngestView(APIView):
    """Template ingestion - admin only."""
    authentication_classes = []
    permission_classes = [IsAdminUser]

    @extend_schema(
        tags=['Admin'],
        summary='Run Template Ingestion',
        description='Run the full template ingestion process. Requires admin authentication. This will load templates from enriched_templates.json, generate embeddings using OpenAI API, and store templates in the database. Warning: This will call OpenAI API and may take several minutes. Note: By default, this clears existing data before ingestion.',
        request=TemplateIngestRequestSerializer,
        responses={200: OpenApiResponse(description='Ingestion completed'), 400: OpenApiResponse(description='Invalid request'), 403: OpenApiResponse(description='Admin authentication required')}
    )
    def post(self, request):
        request_serializer = TemplateIngestRequestSerializer(data=request.data)
        if not request_serializer.is_valid():
            return Response(
                {"error": "Invalid request", "details": request_serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        data = request_serializer.validated_data

        from .services.ingest import ingest_templates

        start_time = datetime.utcnow()

        try:
            ingest_templates(
                json_path=data.get('json_path'),
                batch_size=data.get('batch_size', 100),
                clear_existing=data.get('clear_existing', True)
            )

            search_service = TemplateSearchService()
            validation = search_service.validate_database()

            duration = (datetime.utcnow() - start_time).total_seconds()

            return Response({
                "status": "success",
                "templates_processed": validation['total_templates'],
                "templates_with_embeddings": validation['with_embeddings'],
                "is_valid": validation['is_valid'],
                "duration_seconds": round(duration, 2)
            })

        except Exception as e:
            return Response(
                {"error": "Ingestion failed", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TemplateValidateView(APIView):
    """Database validation - admin only."""
    authentication_classes = []
    permission_classes = [IsAdminUser]

    @extend_schema(
        tags=['Admin'],
        summary='Validate Database',
        description='Validate database integrity - check all templates have embeddings and content',
        responses={200: OpenApiResponse(description='Validation results'), 403: OpenApiResponse(description='Admin authentication required')}
    )
    def get(self, request):
        search_service = TemplateSearchService()
        results = search_service.validate_database()

        return Response({
            "is_valid": results['is_valid'],
            "total_templates": results['total_templates'],
            "with_embeddings": results['with_embeddings'],
            "empty_content": results['empty_content'],
            "checks": {
                "all_have_embeddings": results['with_embeddings'] == results['total_templates'],
                "no_empty_content": results['empty_content'] == 0
            }
        })
