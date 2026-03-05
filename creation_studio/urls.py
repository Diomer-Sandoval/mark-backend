"""
URL Configuration for Template API.

All API endpoints are prefixed with /api/ in the main urls.py
"""

from django.urls import path
from . import views_api

urlpatterns = [
    # Health check
    path('health/', views_api.HealthCheckView.as_view(), name='health-check'),
    
    # Template endpoints
    path('templates/', views_api.TemplateListView.as_view(), name='template-list'),
    path('templates/stats/', views_api.TemplateStatsView.as_view(), name='template-stats'),
    path('templates/search/', views_api.TemplateSearchView.as_view(), name='template-search'),
    path('templates/<str:template_id>/', views_api.TemplateDetailView.as_view(), name='template-detail'),
    
    # Admin endpoints
    path('admin/ingest/', views_api.TemplateIngestView.as_view(), name='template-ingest'),
    path('admin/validate/', views_api.TemplateValidateView.as_view(), name='template-validate'),
]
