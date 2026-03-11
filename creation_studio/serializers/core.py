"""
Serializers for Core Creation Studio Models.

Provides serializers for:
- Brands and Brand DNA
- Creations and Generations
- Previews and Preview Items
- Posts and Platform Insights
"""

from rest_framework import serializers
from ..models import (
    Brand, BrandDNA, Creation, Generation,
    Preview, PreviewItem, Post, PlatformInsight
)


# ============ Brand DNA Serializers ============

class BrandDNASerializer(serializers.ModelSerializer):
    """
    Serializer for BrandDNA model.

    Handles serialization of brand DNA including colors, typography, and voice.
    """

    class Meta:
        model = BrandDNA
        fields = [
            'uuid', 'primary_color', 'secondary_color', 'accent_color',
            'complementary_color', 'font_body_family', 'font_headings_family',
            'voice_tone', 'keywords', 'description', 'archetype', 'target_audience',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['uuid', 'created_at', 'updated_at']


class BrandDNACreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating BrandDNA.
    """

    class Meta:
        model = BrandDNA
        fields = [
            'primary_color', 'secondary_color', 'accent_color',
            'complementary_color', 'font_body_family', 'font_headings_family',
            'voice_tone', 'keywords', 'description', 'archetype', 'target_audience'
        ]


# ============ Brand Serializers ============

class BrandListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for brand list views.
    """

    dna_uuid = serializers.CharField(source='dna.uuid', read_only=True, default=None)

    class Meta:
        model = Brand
        fields = [
            'uuid', 'name', 'slug', 'industry', 'is_active',
            'dna_uuid', 'logo_url', 'created_at'
        ]


class BrandDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for Brand model.
    """

    dna = BrandDNASerializer(read_only=True)

    class Meta:
        model = Brand
        fields = [
            'uuid', 'name', 'slug', 'page_url', 'logo_url',
            'is_active', 'industry', 'user_id', 'tenant_id', 'dna',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['uuid', 'created_at', 'updated_at']


class BrandCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new Brand.
    """

    dna_data = BrandDNACreateSerializer(required=False, write_only=True)

    class Meta:
        model = Brand
        fields = [
            'name', 'slug', 'page_url', 'logo_url',
            'is_active', 'industry', 'user_id', 'tenant_id', 'dna_data'
        ]

    def create(self, validated_data):
        dna_data = validated_data.pop('dna_data', None)

        dna = None
        if dna_data:
            dna = BrandDNA.objects.create(**dna_data)

        brand = Brand.objects.create(dna=dna, **validated_data)
        return brand


class BrandUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating Brand.
    """

    class Meta:
        model = Brand
        fields = [
            'name', 'slug', 'page_url', 'logo_url',
            'is_active', 'industry', 'user_id', 'tenant_id'
        ]


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
    children = serializers.SerializerMethodField()

    class Meta:
        model = Generation
        fields = [
            'uuid', 'creation_uuid', 'parent_uuid',
            'type', 'prompt', 'status', 'content',
            'children', 'created_at'
        ]

    def get_children(self, obj):
        children = obj.children.all()
        return GenerationListSerializer(children, many=True).data


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


# ============ Post Serializers ============

class PostListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for Post list views.
    """

    brand_uuid = serializers.CharField(source='brand.uuid', read_only=True)
    preview_uuid = serializers.CharField(source='preview.uuid', read_only=True, default=None)

    class Meta:
        model = Post
        fields = [
            'uuid', 'brand_uuid', 'preview_uuid',
            'status', 'scheduled_date', 'post_type',
            'platforms', 'created_at'
        ]


class PostDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for Post model.
    """

    brand_uuid = serializers.CharField(source='brand.uuid', read_only=True)
    preview = PreviewDetailSerializer(read_only=True)

    class Meta:
        model = Post
        fields = [
            'uuid', 'brand_uuid', 'user_id', 'preview',
            'final_copy', 'status', 'scheduled_date', 'executed_at',
            'post_type', 'platforms',
            'likes', 'comments', 'shares', 'reach', 'engagement_rate',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['uuid', 'created_at', 'updated_at']


class PostCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new Post.
    """

    class Meta:
        model = Post
        fields = [
            'brand', 'user_id', 'preview', 'final_copy', 'status',
            'scheduled_date', 'post_type', 'platforms'
        ]


class PostUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating Post.
    """

    class Meta:
        model = Post
        fields = [
            'final_copy', 'status', 'scheduled_date', 'executed_at',
            'likes', 'comments', 'shares', 'reach',
            'engagement_rate'
        ]


class PostMetricsUpdateSerializer(serializers.Serializer):
    """
    Serializer for updating post metrics.
    """
    likes = serializers.IntegerField(required=False)
    comments = serializers.IntegerField(required=False)
    shares = serializers.IntegerField(required=False)
    reach = serializers.IntegerField(required=False)


# ============ Platform Insight Serializers ============

class PlatformInsightSerializer(serializers.ModelSerializer):
    """
    Serializer for PlatformInsight model.
    """

    brand_uuid = serializers.CharField(source='brand.uuid', read_only=True)
    brand_name = serializers.CharField(source='brand.name', read_only=True)

    class Meta:
        model = PlatformInsight
        fields = [
            'uuid', 'brand_uuid', 'brand_name',
            'platform', 'date', 'followers',
            'impressions', 'reach', 'engagement_rate',
            'created_at'
        ]
        read_only_fields = ['uuid', 'created_at']


class PlatformInsightCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating PlatformInsight.
    """

    class Meta:
        model = PlatformInsight
        fields = [
            'brand', 'platform', 'date', 'followers',
            'impressions', 'reach', 'engagement_rate'
        ]


class PlatformInsightBulkCreateSerializer(serializers.Serializer):
    """
    Serializer for bulk creating PlatformInsights.
    """
    brand = serializers.PrimaryKeyRelatedField(queryset=Brand.objects.all())
    insights = PlatformInsightCreateSerializer(many=True)

    def create(self, validated_data):
        brand = validated_data['brand']
        insights_data = validated_data['insights']
        insights = []
        for data in insights_data:
            insights.append(PlatformInsight.objects.create(brand=brand, **data))
        return {'insights': insights}


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
        return obj.generations.count()


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
