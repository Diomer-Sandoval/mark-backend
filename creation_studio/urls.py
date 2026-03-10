"""
URL Configuration for Creation Studio API.

All API endpoints are prefixed with /api/ in the main urls.py
"""

from django.urls import path
from . import views_api
from . import views_core
from . import views_test
from . import views_oauth

urlpatterns = [
    # Development/Testing endpoints
    path('auth/test-token/', views_test.TestTokenView.as_view(), name='test-token'),
    path('auth/status/', views_test.AuthStatusView.as_view(), name='auth-status'),
    path('auth/debug-token/', views_test.DebugTokenView.as_view(), name='debug-token'),
    path('auth/test-sia/', views_test.TestSIAConnectionView.as_view(), name='test-sia'),
    
    # OAuth 2.0 Authentication endpoints
    path('auth/oauth/initiate/', views_oauth.OAuthInitiateView.as_view(), name='oauth-initiate'),
    path('auth/oauth/callback/', views_oauth.OAuthCallbackView.as_view(), name='oauth-callback'),
    path('auth/oauth/status/', views_oauth.OAuthStatusView.as_view(), name='oauth-status'),
    path('auth/oauth/logout/', views_oauth.OAuthLogoutView.as_view(), name='oauth-logout'),
    path('auth/oauth/sso/', views_oauth.SSOLoginView.as_view(), name='oauth-sso'),
    # ============ Health Check ============
    path('health/', views_api.HealthCheckView.as_view(), name='health-check'),
    
    # ============ Template Endpoints (Existing) ============
    path('templates/', views_api.TemplateListView.as_view(), name='template-list'),
    path('templates/stats/', views_api.TemplateStatsView.as_view(), name='template-stats'),
    path('templates/search/', views_api.TemplateSearchView.as_view(), name='template-search'),
    path('templates/<str:template_id>/', views_api.TemplateDetailView.as_view(), name='template-detail'),
    
    # ============ Admin Endpoints (Existing) ============
    path('admin/ingest/', views_api.TemplateIngestView.as_view(), name='template-ingest'),
    path('admin/validate/', views_api.TemplateValidateView.as_view(), name='template-validate'),
    
    # ============ Brand Endpoints ============
    path('brands/', views_core.BrandListView.as_view(), name='brand-list'),
    path('brands/<str:uuid>/', views_core.BrandDetailView.as_view(), name='brand-detail'),
    
    # ============ Brand DNA Endpoints ============
    path('brand-dna/', views_core.BrandDNAListView.as_view(), name='brand-dna-list'),
    path('brand-dna/<str:uuid>/', views_core.BrandDNADetailView.as_view(), name='brand-dna-detail'),
    path('brands/<str:brand_uuid>/dna/', views_core.BrandDNAByBrandView.as_view(), name='brand-dna-by-brand'),
    
    # ============ Creation Endpoints ============
    path('creations/', views_core.CreationListView.as_view(), name='creation-list'),
    path('creations/<str:uuid>/', views_core.CreationDetailView.as_view(), name='creation-detail'),
    
    # ============ Generation Endpoints ============
    path('creations/<str:creation_uuid>/generations/', 
         views_core.GenerationListView.as_view(), 
         name='generation-list'),
    path('generations/<str:uuid>/', 
         views_core.GenerationDetailView.as_view(), 
         name='generation-detail'),
    
    # ============ Post Endpoints ============
    path('posts/', views_core.PostListView.as_view(), name='post-list'),
    path('posts/<str:uuid>/', views_core.PostDetailView.as_view(), name='post-detail'),
    path('posts/<str:uuid>/metrics/', views_core.PostMetricsView.as_view(), name='post-metrics'),
    
    # ============ Platform Insight Endpoints ============
    path('platform-insights/', 
         views_core.PlatformInsightListView.as_view(), 
         name='platform-insight-list'),
    path('platform-insights/bulk/', 
         views_core.PlatformInsightBulkCreateView.as_view(), 
         name='platform-insight-bulk'),
    path('platform-insights/<str:uuid>/', 
         views_core.PlatformInsightDetailView.as_view(), 
         name='platform-insight-detail'),
    
    # ============ Media File Endpoints ============
    path('generations/<str:generation_uuid>/media/', 
         views_core.MediaFileListView.as_view(), 
         name='media-file-list'),
    path('media-files/<str:uuid>/', 
         views_core.MediaFileDetailView.as_view(), 
         name='media-file-detail'),
]
