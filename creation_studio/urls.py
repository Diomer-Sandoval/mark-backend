"""
URL Configuration for Creation Studio API.

All API endpoints are prefixed with /api/ in the main urls.py
"""

from django.urls import path
from .views import core as views_core
from .views.content import generate as generate_view

urlpatterns = [
    # ============ Creation Endpoints ============
    path('creations/', views_core.CreationListView.as_view(), name='creation-list'),
    path('creations/<str:uuid>/', views_core.CreationDetailView.as_view(), name='creation-detail'),
    
    # ============ Generation Endpoints ============
    path('generations/', generate_view, name='generation-create'),
    path('creations/<str:creation_uuid>/generations/',
         views_core.GenerationListView.as_view(),
         name='generation-list'),
    path('generations/<str:uuid>/',
         views_core.GenerationDetailView.as_view(),
         name='generation-detail'),
    
    # ============ Preview Endpoints ============
    path('previews/', views_core.PreviewListView.as_view(), name='preview-list'),
    path('previews/<str:uuid>/', views_core.PreviewDetailView.as_view(), name='preview-detail'),
    path('previews/<str:preview_uuid>/items/', views_core.PreviewItemListView.as_view(), name='preview-item-list'),
]
