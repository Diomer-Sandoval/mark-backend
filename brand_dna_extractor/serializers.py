from rest_framework import serializers
from .models import Brand, BrandDNA

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
