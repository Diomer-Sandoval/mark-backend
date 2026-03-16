from django.contrib import admin
from .models import Post, PlatformInsight

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'brand', 'status', 'scheduled_date', 'engagement_rate')
    list_filter = ('status', 'post_type')
    search_fields = ('final_copy',)
    readonly_fields = ('uuid', 'created_at', 'updated_at')


@admin.register(PlatformInsight)
class PlatformInsightAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'brand', 'platform', 'date', 'followers', 'reach', 'engagement_rate')
    list_filter = ('platform',)
    search_fields = ('brand__name',)
    readonly_fields = ('uuid', 'created_at')
    date_hierarchy = 'date'
