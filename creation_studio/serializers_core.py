"""
Serializers for Core Creation Studio Models.

Provides serializers for:
- Brands and Brand DNA
- Creations and Generations
- Posts and Platform Insights
- Media Files
"""

from rest_framework import serializers
from .models_core import (
    Brand, BrandDNA, Creation, Generation,
    Post, PlatformInsight, MediaFile
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
            'voice_tone', 'keywords', 'description',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['uuid', 'created_at', 'updated_at']


class BrandDNACreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating BrandDNA.
    
    Accepts raw extraction data and creates a BrandDNA record.
    
    Example:
        {
            "primary_color": "#007AFF",
            "secondary_color": "#FFFFFF",
            "accent_color": "#FF9500",
            "complementary_color": "#34C759",
            "font_body_family": "Inter",
            "font_headings_family": "Montserrat",
            "voice_tone": "Professional, friendly, innovative",
            "keywords": "technology, innovation, premium",
            "description": "A modern tech brand focused on innovation"
        }
    """
    
    class Meta:
        model = BrandDNA
        fields = [
            'primary_color', 'secondary_color', 'accent_color',
            'complementary_color', 'font_body_family', 'font_headings_family',
            'voice_tone', 'keywords', 'description'
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
    
    Includes full BrandDNA nested serialization.
    """
    
    dna = BrandDNASerializer(read_only=True)
    
    class Meta:
        model = Brand
        fields = [
            'uuid', 'name', 'slug', 'page_url', 'logo_url',
            'is_active', 'industry', 'user_id', 'dna',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['uuid', 'created_at', 'updated_at']


class BrandCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new Brand.
    
    Optionally accepts dna_data to create BrandDNA simultaneously.
    """
    
    dna_data = BrandDNACreateSerializer(required=False, write_only=True)
    
    class Meta:
        model = Brand
        fields = [
            'name', 'slug', 'page_url', 'logo_url',
            'is_active', 'industry', 'user_id', 'dna_data'
        ]
    
    def create(self, validated_data):
        dna_data = validated_data.pop('dna_data', None)
        
        # Create BrandDNA if data provided
        dna = None
        if dna_data:
            dna = BrandDNA.objects.create(**dna_data)
        
        # Create Brand
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
            'is_active', 'industry', 'user_id'
        ]


# ============ Media File Serializers ============

class MediaFileSerializer(serializers.ModelSerializer):
    """
    Serializer for MediaFile model.
    """
    
    generation_uuid = serializers.CharField(source='generation.uuid', read_only=True)
    
    class Meta:
        model = MediaFile
        fields = [
            'uuid', 'generation_uuid', 'url', 'file_type',
            'file_size', 'width', 'height',
            'storage_provider', 'created_at'
        ]
        read_only_fields = ['uuid', 'created_at']


class MediaFileCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating MediaFile.
    """
    
    class Meta:
        model = MediaFile
        fields = [
            'generation', 'url', 'file_type',
            'file_size', 'width', 'height', 'storage_provider'
        ]


# ============ Generation Serializers ============

class GenerationListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for Generation list views.
    """
    
    creation_uuid = serializers.CharField(source='creation.uuid', read_only=True)
    parent_uuid = serializers.CharField(source='parent.uuid', read_only=True, default=None)
    media_files = MediaFileSerializer(many=True, read_only=True)
    
    class Meta:
        model = Generation
        fields = [
            'uuid', 'creation_uuid', 'parent_uuid',
            'media_type', 'status', 'prompt',
            'media_files', 'created_at'
        ]


class GenerationDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for Generation model.
    """
    
    creation_uuid = serializers.CharField(source='creation.uuid', read_only=True)
    parent_uuid = serializers.CharField(source='parent.uuid', read_only=True, default=None)
    media_files = MediaFileSerializer(many=True, read_only=True)
    children = serializers.SerializerMethodField()
    
    class Meta:
        model = Generation
        fields = [
            'uuid', 'creation_uuid', 'parent_uuid',
            'media_type', 'prompt', 'status',
            'generation_params', 'media_files',
            'children', 'created_at'
        ]
    
    def get_children(self, obj):
        """Get child generations (versions of this generation)."""
        children = obj.children.all()
        return GenerationListSerializer(children, many=True).data


class GenerationCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new Generation.
    """
    
    class Meta:
        model = Generation
        fields = [
            'creation', 'parent', 'media_type',
            'prompt', 'status', 'generation_params'
        ]


class GenerationUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating Generation status.
    """
    
    class Meta:
        model = Generation
        fields = ['status', 'prompt', 'generation_params']


# ============ Post Serializers ============

class PostListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for Post list views.
    """
    
    brand_uuid = serializers.CharField(source='brand.uuid', read_only=True)
    creation_uuid = serializers.CharField(source='creation.uuid', read_only=True, default=None)
    
    class Meta:
        model = Post
        fields = [
            'uuid', 'brand_uuid', 'creation_uuid',
            'status', 'scheduled_date', 'post_type',
            'platforms', 'created_at'
        ]


class PostDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for Post model.
    
    Includes full performance metrics.
    """
    
    brand_uuid = serializers.CharField(source='brand.uuid', read_only=True)
    creation_uuid = serializers.CharField(source='creation.uuid', read_only=True, default=None)
    
    class Meta:
        model = Post
        fields = [
            'uuid', 'brand_uuid', 'creation_uuid',
            'copy', 'status', 'scheduled_date', 'executed_at',
            'post_type', 'platforms',
            'likes', 'comments', 'shares', 'reach', 'engagement_rate',
            'metrics', 'created_at', 'updated_at'
        ]
        read_only_fields = ['uuid', 'created_at', 'updated_at']


class PostCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new Post.
    """
    
    class Meta:
        model = Post
        fields = [
            'brand', 'creation', 'copy', 'status',
            'scheduled_date', 'post_type', 'platforms'
        ]


class PostUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating Post.
    
    Allows updating content and metrics.
    """
    
    class Meta:
        model = Post
        fields = [
            'copy', 'status', 'scheduled_date', 'executed_at',
            'likes', 'comments', 'shares', 'reach',
            'engagement_rate', 'metrics'
        ]


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
            'metrics', 'created_at'
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
            'impressions', 'reach', 'engagement_rate', 'metrics'
        ]


class PlatformInsightBulkCreateSerializer(serializers.Serializer):
    """
    Serializer for bulk creating PlatformInsight records.
    """
    
    insights = PlatformInsightCreateSerializer(many=True)
    
    def create(self, validated_data):
        insights_data = validated_data.get('insights', [])
        created = []
        for insight_data in insights_data:
            insight = PlatformInsight.objects.create(**insight_data)
            created.append(insight)
        return {'insights': created}


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
    
    Includes nested generations and brand info.
    """
    
    brand_uuid = serializers.CharField(source='brand.uuid', read_only=True)
    brand_name = serializers.CharField(source='brand.name', read_only=True)
    generations = GenerationListSerializer(many=True, read_only=True)
    posts = PostListSerializer(many=True, read_only=True)
    
    class Meta:
        model = Creation
        fields = [
            'uuid', 'brand_uuid', 'brand_name', 'title',
            'post_type', 'status', 'platforms', 'post_tone',
            'original_prompt', 'research_data',
            'generations', 'posts',
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
            'platforms', 'post_tone', 'original_prompt'
        ]


class CreationUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating Creation.
    """
    
    class Meta:
        model = Creation
        fields = [
            'title', 'post_type', 'status',
            'platforms', 'post_tone', 'original_prompt', 'research_data'
        ]


# ============ Request/Input Serializers ============

class CreationSearchRequestSerializer(serializers.Serializer):
    """
    Serializer for creation search/filter request.
    """
    
    brand_uuid = serializers.CharField(required=False)
    status = serializers.CharField(required=False)
    post_type = serializers.CharField(required=False)
    search = serializers.CharField(required=False, help_text="Search in title")


class PostMetricsUpdateSerializer(serializers.Serializer):
    """
    Serializer for updating post metrics.
    """
    
    likes = serializers.IntegerField(required=False, min_value=0)
    comments = serializers.IntegerField(required=False, min_value=0)
    shares = serializers.IntegerField(required=False, min_value=0)
    reach = serializers.IntegerField(required=False, min_value=0)
    engagement_rate = serializers.FloatField(required=False, min_value=0)
