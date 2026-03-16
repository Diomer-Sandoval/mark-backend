from rest_framework import serializers
from .models import Post, PlatformInsight
from brand_dna_extractor.models import Brand
from creation_studio.serializers import PreviewDetailSerializer

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
            'uuid', 'brand_uuid', 'preview',
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
            'brand', 'preview', 'final_copy', 'status',
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
