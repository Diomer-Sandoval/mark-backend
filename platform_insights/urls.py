from django.urls import path
from .views import SyncInsightsView

urlpatterns = [
    path('sync/', SyncInsightsView.as_view(), name='sync-insights'),
]
