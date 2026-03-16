from django.contrib import admin
from .models import Brand, BrandDNA

@admin.register(BrandDNA)
class BrandDNAAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'primary_color', 'voice_tone', 'font_body_family', 'archetype')
    search_fields = ('voice_tone', 'keywords', 'description', 'archetype')
    readonly_fields = ('uuid', 'created_at', 'updated_at')


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'name', 'slug', 'industry', 'is_active', 'user_id', 'created_at')
    list_filter = ('is_active', 'industry')
    search_fields = ('name', 'slug', 'user_id')
    readonly_fields = ('uuid', 'created_at', 'updated_at')
