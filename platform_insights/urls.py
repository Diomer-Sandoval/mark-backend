from django.urls import path
from .views import (
    SyncInsightsView,
    PostListView, PostDetailView, PostMetricsView,
    PlatformInsightListView, PlatformInsightBulkCreateView, PlatformInsightDetailView
)

urlpatterns = [
    # Meta Sync
    path('insights/sync/', SyncInsightsView.as_view(), name='sync-insights'),
    
    # Posts
    path('posts/', PostListView.as_view(), name='post-list'),
    path('posts/<uuid:uuid>/', PostDetailView.as_view(), name='post-detail'),
    path('posts/<uuid:uuid>/metrics/', PostMetricsView.as_view(), name='post-metrics'),
    
    # Platform Insights
    path('platform-insights/', PlatformInsightListView.as_view(), name='platform-insight-list'),
    path('platform-insights/bulk/', PlatformInsightBulkCreateView.as_view(), name='platform-insight-bulk'),
    path('platform-insights/<uuid:uuid>/', PlatformInsightDetailView.as_view(), name='platform-insight-detail'),
]
