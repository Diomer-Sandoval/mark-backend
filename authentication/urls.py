from django.urls import path
from .views import (
    OAuthInitiateView,
    OAuthCallbackView,
    OAuthStatusView,
    OAuthLogoutView,
    SSOLoginView
)
from .views_dev import (
    TestTokenView,
    AuthStatusView,
    DebugTokenView,
    TestSIAConnectionView
)

urlpatterns = [
    # Development/Testing endpoints
    path('test-token/', TestTokenView.as_view(), name='test-token'),
    path('status/', AuthStatusView.as_view(), name='auth-status'),
    path('debug-token/', DebugTokenView.as_view(), name='debug-token'),
    path('test-sia/', TestSIAConnectionView.as_view(), name='test-sia'),
    
    # OAuth 2.0 Authentication endpoints
    path('oauth/initiate/', OAuthInitiateView.as_view(), name='oauth-initiate'),
    path('oauth/callback/', OAuthCallbackView.as_view(), name='oauth-callback'),
    path('oauth/status/', OAuthStatusView.as_view(), name='oauth-status'),
    path('oauth/logout/', OAuthLogoutView.as_view(), name='oauth-logout'),
    path('oauth/sso/', SSOLoginView.as_view(), name='oauth-sso'),
]
