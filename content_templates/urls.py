from django.urls import path
from .views import (
    HealthCheckView,
    TemplateListView,
    TemplateStatsView,
    TemplateSearchView,
    TemplateDetailView,
    TemplateIngestView,
    TemplateValidateView
)

urlpatterns = [
    # ============ Health Check ============
    path('health/', HealthCheckView.as_view(), name='health-check'),
    
    # ============ Template Endpoints ============
    path('', TemplateListView.as_view(), name='template-list'),
    path('stats/', TemplateStatsView.as_view(), name='template-stats'),
    path('search/', TemplateSearchView.as_view(), name='template-search'),
    path('<str:template_id>/', TemplateDetailView.as_view(), name='template-detail'),
    
    # ============ Admin Endpoints ============
    path('admin/ingest/', TemplateIngestView.as_view(), name='template-ingest'),
    path('admin/validate/', TemplateValidateView.as_view(), name='template-validate'),
]
