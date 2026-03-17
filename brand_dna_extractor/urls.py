from django.urls import path
from .views import (
    extract,
    BrandListView, BrandDetailView,
    BrandDNAListView, BrandDNADetailView, BrandDNAByBrandView
)

urlpatterns = [
    # AI Extraction
    path('extract/', extract, name='brand-extract'),
    
    # Brands (prefix should be /api/brands/)
    path('', BrandListView.as_view(), name='brand-list'),
    path('<uuid:uuid>/', BrandDetailView.as_view(), name='brand-detail'),
    
    # Brand DNA (prefix should be /api/brand-dna/)
    path('brand-dna/', BrandDNAListView.as_view(), name='brand-dna-list'),
    path('brand-dna/<uuid:uuid>/', BrandDNADetailView.as_view(), name='brand-dna-detail'),
    path('<uuid:brand_uuid>/dna/', BrandDNAByBrandView.as_view(), name='brand-dna-by-brand'),
]
