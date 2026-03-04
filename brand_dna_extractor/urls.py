from django.urls import path
from .views import extract

urlpatterns = [
    path('extract/', extract),
]
