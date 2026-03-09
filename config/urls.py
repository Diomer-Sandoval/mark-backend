"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from creation_studio.views import (
    generate_content,
    regenerate_copy,
    edit_image,
    generate_carousel,
    edit_carousel_slide,
    generate_video,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/content/generate-video/", generate_video),
    path("api/content/generate-image/", generate_content),
    path("api/content/edit-image/", edit_image),
    path("api/content/edit-copy/", regenerate_copy),
    path("api/content/generate-carousel/", generate_carousel),
    path("api/content/edit-carousel-slide/", edit_carousel_slide),
    path("api/brand-dna/", include("brand_dna_extractor.urls")),
]
