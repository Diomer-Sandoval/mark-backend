from django.contrib import admin
from .models import TemplateDocument

@admin.register(TemplateDocument)
class TemplateDocumentAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_template_id', 'get_title', 'get_template_type', 'created_at')
    search_fields = ('content', 'metadata')
    readonly_fields = ('created_at', 'updated_at')

    def get_template_id(self, obj):
        return obj.metadata.get('id', '-')
    get_template_id.short_description = 'Template ID'

    def get_title(self, obj):
        return obj.metadata.get('title', '-')[:60]
    get_title.short_description = 'Title'

    def get_template_type(self, obj):
        return obj.metadata.get('template_type', '-')
    get_template_type.short_description = 'Type'
