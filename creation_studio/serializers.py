"""
Serializers for Core Creation Studio Models.

Provides serializers for:
- Creations and Generations
- Previews and Preview Items
"""

from rest_framework import serializers
from .models import (
    Creation, Generation,
    Preview, PreviewItem
)


# ============ Generation Serializers ============


class GenerationListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for Generation list views.
    """

    creation_uuid = serializers.CharField(source='creation.uuid', read_only=True)
    parent_uuid = serializers.CharField(source='parent.uuid', read_only=True, default=None)

    class Meta:
        model = Generation
        fields = [
            'uuid', 'creation_uuid', 'parent_uuid',
            'type', 'status', 'prompt', 'content', 'created_at'
        ]


class GenerationDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for Generation model.
    """

    creation_uuid = serializers.CharField(source='creation.uuid', read_only=True)
    parent_uuid = serializers.CharField(source='parent.uuid', read_only=True, default=None)
    slices = serializers.SerializerMethodField()

    class Meta:
        model = Generation
        fields = [
            'uuid', 'creation_uuid', 'parent_uuid',
            'type', 'prompt', 'status', 'content',
            'slices', 'created_at'
        ]

    def get_slices(self, obj):
        """If this is a master generation (carousel/video), return its child generations."""
        if obj.type in ["carousel", "video"] and obj.content:
            try:
                # Content stores comma-separated UUIDs of child generations
                uuids = [u.strip() for u in obj.content.split(",") if u.strip()]
                if uuids:
                    # Fetch and serialize children
                    children = Generation.objects.filter(uuid__in=uuids)
                    # Maintain order from the content string
                    uuid_to_child = {str(child.uuid): child for child in children}
                    ordered_children = [uuid_to_child[u] for u in uuids if u in uuid_to_child]
                    return GenerationListSerializer(ordered_children, many=True).data
            except Exception:
                pass
        return []


class GenerationCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new Generation.
    """

    class Meta:
        model = Generation
        fields = [
            'creation', 'parent', 'type',
            'prompt', 'status', 'content'
        ]


class GenerationUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating Generation.
    """

    class Meta:
        model = Generation
        fields = ['status', 'prompt', 'content']


# ============ Preview Serializers ============

class PreviewItemSerializer(serializers.ModelSerializer):
    """
    Serializer for PreviewItem model.
    """
    generation = GenerationListSerializer(read_only=True)
    generation_uuid = serializers.PrimaryKeyRelatedField(
        queryset=Generation.objects.all(), source='generation', write_only=True
    )

    class Meta:
        model = PreviewItem
        fields = ['uuid', 'generation', 'generation_uuid', 'position']


class PreviewDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for Preview model.
    """
    items = PreviewItemSerializer(many=True, read_only=True)

    class Meta:
        model = Preview
        fields = ['uuid', 'version_name', 'internal_notes', 'items', 'created_at', 'updated_at']
        read_only_fields = ['uuid', 'created_at', 'updated_at']


class PreviewCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a Preview.
    """
    class Meta:
        model = Preview
        fields = ['version_name', 'internal_notes']


# ============ Creation Serializers ============

class CreationListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for Creation list views.
    """

    brand_uuid = serializers.CharField(source='brand.uuid', read_only=True)
    brand_name = serializers.CharField(source='brand.name', read_only=True)
    generation_count = serializers.SerializerMethodField()

    class Meta:
        model = Creation
        fields = [
            'uuid', 'brand_uuid', 'brand_name', 'title',
            'post_type', 'status', 'platforms',
            'generation_count', 'created_at', 'updated_at'
        ]

    def get_generation_count(self, obj):
        return getattr(obj, 'generation_count', obj.generations.count())


class CreationDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for Creation model.
    """

    brand_uuid = serializers.CharField(source='brand.uuid', read_only=True)
    brand_name = serializers.CharField(source='brand.name', read_only=True)
    generations = GenerationListSerializer(many=True, read_only=True)

    class Meta:
        model = Creation
        fields = [
            'uuid', 'brand_uuid', 'brand_name', 'title',
            'post_type', 'status', 'platforms', 'post_tone',
            'generations',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['uuid', 'created_at', 'updated_at']


class CreationCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new Creation project.
    """

    class Meta:
        model = Creation
        fields = [
            'brand', 'title', 'post_type', 'status',
            'platforms', 'post_tone'
        ]


class CreationUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating Creation.
    """

    class Meta:
        model = Creation
        fields = [
            'title', 'post_type', 'status',
            'platforms', 'post_tone'
        ]

# Compatibility/Imports from other apps - MOVED TO END TO PREVENT CIRCULAR IMPORTS
from brand_dna_extractor.serializers import (
    BrandDNASerializer,
    BrandDNACreateSerializer,
    BrandListSerializer,
    BrandDetailSerializer,
    BrandCreateSerializer,
    BrandUpdateSerializer,
)
from platform_insights.serializers import (
    PostListSerializer,
    PostDetailSerializer,
    PostCreateSerializer,
    PostUpdateSerializer,
    PostMetricsUpdateSerializer,
    PlatformInsightSerializer,
    PlatformInsightCreateSerializer,
    PlatformInsightBulkCreateSerializer,
)
