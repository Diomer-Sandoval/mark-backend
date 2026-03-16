"""
URL configuration for the MARK project.
"""

from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    # Django Admin
    path('admin/', admin.site.urls),

    # API Endpoints
    path('api/auth/', include('authentication.urls')),
    path('api/templates/', include('content_templates.urls')),
    path('api/studio/', include('creation_studio.urls')),
    path('api/brand/', include('brand_dna_extractor.urls')),
    path('api/insights/', include('platform_insights.urls')),
    path('api/chatbot/', include('ai_chatbot.urls')),

    # Swagger/OpenAPI Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
