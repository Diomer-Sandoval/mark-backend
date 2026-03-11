from django.contrib import admin

from .models import (
    Brand,
    BrandDNA,
    Creation,
    Generation,
    Post,
    PlatformInsight,
    Preview,
    PreviewItem,
    TemplateDocument,
)


@admin.register(BrandDNA)
class BrandDNAAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'primary_color', 'voice_tone', 'font_body_family', 'archetype')
    search_fields = ('voice_tone', 'keywords', 'description', 'archetype')
    readonly_fields = ('uuid', 'created_at', 'updated_at')


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'name', 'slug', 'industry', 'is_active', 'user_id', 'tenant_id', 'created_at')
    list_filter = ('is_active', 'industry')
    search_fields = ('name', 'slug', 'user_id', 'tenant_id')
    readonly_fields = ('uuid', 'created_at', 'updated_at')


@admin.register(Creation)
class CreationAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'title', 'post_type', 'status', 'brand', 'created_at')
    list_filter = ('status', 'post_type')
    search_fields = ('title', 'post_tone', 'platforms')
    readonly_fields = ('uuid', 'created_at', 'updated_at')


@admin.register(Generation)
class GenerationAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'creation', 'type', 'status', 'parent', 'created_at')
    list_filter = ('status', 'type')
    search_fields = ('uuid', 'prompt', 'content')
    readonly_fields = ('uuid', 'created_at')


@admin.register(Preview)
class PreviewAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'version_name', 'created_at')
    search_fields = ('version_name', 'internal_notes')
    readonly_fields = ('uuid', 'created_at', 'updated_at')


@admin.register(PreviewItem)
class PreviewItemAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'preview', 'generation', 'position')
    list_filter = ('preview',)
    readonly_fields = ('uuid',)


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'brand', 'status', 'user_id', 'scheduled_date', 'engagement_rate')
    list_filter = ('status', 'post_type', 'platforms')
    search_fields = ('final_copy', 'user_id')
    readonly_fields = ('uuid', 'created_at', 'updated_at')


@admin.register(PlatformInsight)
class PlatformInsightAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'brand', 'platform', 'date', 'followers', 'reach', 'engagement_rate')
    list_filter = ('platform',)
    search_fields = ('brand__name',)
    readonly_fields = ('uuid', 'created_at')
    date_hierarchy = 'date'


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
