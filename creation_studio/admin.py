from django.contrib import admin

from .models import (
    Creation,
    Generation,
    Preview,
    PreviewItem,
)


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
