"""
Serializers for Template API.

Converts TemplateDocument model instances to/from JSON for API responses.
"""

from rest_framework import serializers
from .models import TemplateDocument


class TemplateMetadataSerializer(serializers.Serializer):
    """
    Serializer for template metadata fields.
    
    Extracts key fields from the metadata JSON for API responses.
    """
    id = serializers.CharField(source='metadata.id')
    title = serializers.CharField(source='metadata.title', default='')
    source_platform = serializers.CharField(source='metadata.source_platform', default='')
    source_url = serializers.CharField(source='metadata.source_url', default='')
    preview_image_url = serializers.CharField(source='metadata.preview_image_url', default='')
    preview_image_path = serializers.CharField(source='metadata.preview_image_path', default='')
    template_type = serializers.CharField(source='metadata.template_type', default='')
    sub_type = serializers.CharField(source='metadata.sub_type', default='')
    category = serializers.CharField(source='metadata.category', default='')
    price = serializers.CharField(source='metadata.price', default='')
    file_format = serializers.CharField(source='metadata.file_format', default='')
    ai_description = serializers.CharField(source='metadata.ai_description', default='')
    design_style = serializers.CharField(source='metadata.design_style', default='')
    color_palette = serializers.ListField(source='metadata.color_palette', default=list)
    use_cases = serializers.ListField(source='metadata.use_cases', default=list)
    industry_fit = serializers.ListField(source='metadata.industry_fit', default=list)
    content_elements = serializers.ListField(source='metadata.content_elements', default=list)
    keywords = serializers.ListField(source='metadata.keywords', default=list)
    mood = serializers.ListField(source='metadata.mood', default=list)
    text_heavy = serializers.BooleanField(source='metadata.text_heavy', default=False)
    customization_flexibility = serializers.CharField(source='metadata.customization_flexibility', default='')
    target_platforms = serializers.ListField(source='metadata.target_platforms', default=list)


class TemplateDocumentSerializer(serializers.ModelSerializer):
    """
    Full serializer for TemplateDocument model.
    
    Includes all fields with metadata expanded.
    """
    metadata = TemplateMetadataSerializer(read_only=True)
    
    class Meta:
        model = TemplateDocument
        fields = ['id', 'content', 'metadata', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class TemplateListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for template list views.
    
    Only includes essential fields for listing.
    """
    id = serializers.CharField(source='metadata.id')
    title = serializers.CharField(source='metadata.title', default='')
    template_type = serializers.CharField(source='metadata.template_type', default='')
    design_style = serializers.CharField(source='metadata.design_style', default='')
    preview_image_url = serializers.CharField(source='metadata.preview_image_url', default='')
    preview_image_path = serializers.CharField(source='metadata.preview_image_path', default='')
    
    class Meta:
        model = TemplateDocument
        fields = ['id', 'title', 'template_type', 'design_style', 
                  'preview_image_url', 'preview_image_path', 'created_at']


class TemplateSearchResultSerializer(serializers.Serializer):
    """
    Serializer for template search results.
    
    Includes the template data and similarity score.
    Data structure: {'template': TemplateDocument, 'similarity': float}
    """
    id = serializers.CharField(source='template.metadata.id')
    title = serializers.CharField(source='template.metadata.title', default='')
    template_type = serializers.CharField(source='template.metadata.template_type', default='')
    sub_type = serializers.CharField(source='template.metadata.sub_type', default='')
    design_style = serializers.CharField(source='template.metadata.design_style', default='')
    ai_description = serializers.CharField(source='template.metadata.ai_description', default='')
    preview_image_url = serializers.CharField(source='template.metadata.preview_image_url', default='')
    preview_image_path = serializers.CharField(source='template.metadata.preview_image_path', default='')
    color_palette = serializers.ListField(source='template.metadata.color_palette', default=list)
    use_cases = serializers.ListField(source='template.metadata.use_cases', default=list)
    industry_fit = serializers.ListField(source='template.metadata.industry_fit', default=list)
    keywords = serializers.ListField(source='template.metadata.keywords', default=list)
    mood = serializers.ListField(source='template.metadata.mood', default=list)
    similarity = serializers.FloatField()


# Request/Input Serializers

class TemplateSearchRequestSerializer(serializers.Serializer):
    """
    Serializer for template search request.
    
    Validates incoming search queries.
    """
    query = serializers.CharField(
        required=True,
        max_length=5000,
        help_text="Search query text describing the desired template"
    )
    match_count = serializers.IntegerField(
        required=False,
        default=50,
        min_value=1,
        max_value=100,
        help_text="Number of results to return (1-100, default: 50)"
    )
    filters = serializers.DictField(
        required=False,
        default=dict,
        help_text="Optional filters: template_type, design_style, industry, etc."
    )


class TemplateIngestRequestSerializer(serializers.Serializer):
    """
    Serializer for template ingestion request.
    """
    json_path = serializers.CharField(
        required=False,
        help_text="Path to enriched_templates.json (optional)"
    )
    batch_size = serializers.IntegerField(
        required=False,
        default=100,
        min_value=1,
        max_value=500,
        help_text="Batch size for embedding generation"
    )
    clear_existing = serializers.BooleanField(
        required=False,
        default=True,
        help_text="Clear existing templates before ingestion"
    )


class HealthCheckSerializer(serializers.Serializer):
    """
    Serializer for health check response.
    """
    status = serializers.CharField()
    database = serializers.CharField()
    total_templates = serializers.IntegerField()
    version = serializers.CharField()
    timestamp = serializers.DateTimeField()
