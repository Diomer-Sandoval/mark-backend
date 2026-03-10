"""
OAuth 2.0 Authentication Views for SIA Solutions integration.

This module provides endpoints for:
1. OAuth flow initiation - redirects to SIA login
2. OAuth callback - handles authorization code from SIA
3. Session status - checks if user is authenticated in session
4. Logout - clears session

Flow:
1. User clicks "Mark Agent" in SIA dashboard
2. SIA redirects to /api/auth/oauth/initiate/ with user context
3. We redirect to SIA OAuth authorization endpoint
4. User authorizes (if not already)
5. SIA redirects back to /api/auth/oauth/callback/
6. We exchange code for token and create session
7. Redirect to frontend with token or set session cookie
"""

import secrets
import logging
from urllib.parse import urlencode, parse_qs, urlparse

from django.conf import settings
from django.http import HttpResponseRedirect, JsonResponse
from django.core.cache import cache
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter

from .sia_client import get_sia_client
from .authentication import SIAUser

logger = logging.getLogger(__name__)


class OAuthInitiateView(APIView):
    """
    Initiate OAuth 2.0 flow with SIA Solutions.
    
    This endpoint is called when user clicks on "Mark Agent" from SIA dashboard.
    It redirects to SIA's OAuth authorization endpoint.
    
    Query Parameters:
    - redirect_uri: Where to redirect after OAuth (optional, defaults to FRONTEND_URL)
    - state: Optional state to pass through (for CSRF protection)
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        tags=['Authentication'],
        summary='Initiate OAuth Login',
        description='''
        Initiates OAuth 2.0 flow with SIA Solutions.
        
        This endpoint redirects to SIA's OAuth authorization endpoint.
        
        **Usage:**
        - Call this when user clicks "Login with SIA" or "Mark Agent" in SIA dashboard
        - The user will be redirected to SIA login/authorization page
        - After authorization, SIA redirects to /api/auth/oauth/callback/
        
        **Query Parameters:**
        - `redirect_uri`: Frontend URL to redirect after login (optional)
        - `state`: State parameter for CSRF protection (optional)
        ''',
        parameters=[
            OpenApiParameter(
                name='redirect_uri',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Frontend URL to redirect after login',
                required=False
            ),
            OpenApiParameter(
                name='state',
                type=str,
                location=OpenApiParameter.QUERY,
                description='State parameter for CSRF protection',
                required=False
            ),
        ],
        responses={
            302: OpenApiResponse(description='Redirects to SIA OAuth authorization endpoint'),
            500: OpenApiResponse(description='OAuth not configured')
        }
    )
    def get(self, request):
        # Get SIA configuration
        sia_base_url = getattr(settings, 'SIA_BASE_URL', None)
        sia_frontend_url = getattr(settings, 'SIA_FRONTEND_URL', None)
        mark_frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5174')
        
        if not sia_base_url:
            return Response(
                {'error': 'SIA_BASE_URL not configured'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Get final redirect destination after successful OAuth
        final_redirect = request.query_params.get('redirect_uri')
        if not final_redirect:
            final_redirect = f"{mark_frontend_url}/app/dashboard"
        
        # Get or generate state for CSRF protection
        state = request.query_params.get('state')
        if not state:
            state = secrets.token_urlsafe(32)
        
        # Store state in cache with final redirect (expires in 30 minutes)
        cache_key = f"oauth_state:{state}"
        cache.set(cache_key, {
            'redirect_uri': final_redirect,
            'initiated_at': str(datetime_now()),
        }, timeout=1800)  # 30 minutes
        
        # Build the OAuth callback URL for Mark Frontend
        # This must match EXACTLY what's registered in SIA OAuth client
        mark_callback = f"{mark_frontend_url.rstrip('/')}/auth/callback"
        
        # Redirect to SIA FRONTEND to handle OAuth flow
        if sia_frontend_url:
            params = {
                'client_id': getattr(settings, 'SIA_OAUTH_CLIENT_ID', 'mark-agent'),
                'redirect_uri': mark_callback,
                'state': state,
                'scope': 'openid profile email tenant agents',
                'response_type': 'code',
            }
            authorization_url = f"{sia_frontend_url}/oauth/authorize?{urlencode(params)}"
        else:
            # Fallback: redirect directly to SIA backend
            oauth_url = f"{sia_base_url}/oauth/authorize/"
            params = {
                'response_type': 'code',
                'client_id': getattr(settings, 'SIA_OAUTH_CLIENT_ID', 'mark-agent'),
                'redirect_uri': mark_callback,
                'state': state,
                'scope': 'openid profile email tenant agents',
            }
            authorization_url = f"{oauth_url}?{urlencode(params)}"
        
        # Log OAuth initiation (safe - no sensitive data)
        logger.info(f"OAuth initiated for client: {settings.SIA_OAUTH_CLIENT_ID[:8]}... redirecting to SIA frontend")
        
        return HttpResponseRedirect(authorization_url)


class OAuthCallbackView(APIView):
    """
    Handle OAuth callback from SIA Solutions.
    
    This endpoint receives the authorization code from SIA after user authorizes.
    It exchanges the code for an access token and creates a session.
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        tags=['Authentication'],
        summary='OAuth Callback',
        description='''
        Handles OAuth callback from SIA Solutions.
        
        **This endpoint is called by SIA after user authorization.**
        
        Query Parameters:
        - `code`: Authorization code from SIA
        - `state`: State parameter (must match the one sent during initiation)
        - `error`: Error code (if authorization failed)
        - `error_description`: Error description
        
        After successful authentication, user is redirected to frontend with token.
        ''',
        parameters=[
            OpenApiParameter(
                name='code',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Authorization code from SIA',
                required=False
            ),
            OpenApiParameter(
                name='state',
                type=str,
                location=OpenApiParameter.QUERY,
                description='State parameter for verification',
                required=False
            ),
            OpenApiParameter(
                name='error',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Error code if authorization failed',
                required=False
            ),
        ],
        responses={
            302: OpenApiResponse(description='Redirects to frontend with token or error'),
            400: OpenApiResponse(description='Invalid request')
        }
    )
    def get(self, request):
        # Check for errors
        error = request.query_params.get('error')
        error_description = request.query_params.get('error_description')
        
        if error:
            logger.warning(f"OAuth error: {error} - {error_description}")
            return Response({
                'success': False,
                'error': error,
                'error_description': error_description or 'OAuth authorization failed'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get authorization code and state
        code = request.query_params.get('code')
        state = request.query_params.get('state')
        
        if not code or not state:
            return Response({
                'success': False,
                'error': 'invalid_request',
                'error_description': 'Missing authorization code or state'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify state parameter (CSRF protection)
        cache_key = f"oauth_state:{state}"
        state_data = cache.get(cache_key)
        
        if not state_data:
            return Response({
                'success': False,
                'error': 'invalid_state',
                'error_description': 'State parameter expired or invalid'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Clean up state from cache
        cache.delete(cache_key)
        
        # Get final redirect destination
        final_redirect = state_data.get('redirect_uri', getattr(
            settings, 'FRONTEND_URL', 'http://localhost:5174'))
        
        # Exchange authorization code for access token
        token_data = self._exchange_code_for_token(code, state)
        
        if not token_data:
            return Response({
                'success': False,
                'error': 'token_exchange_failed',
                'error_description': 'Failed to exchange authorization code for token'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get user info using the access token
        access_token = token_data.get('access_token')
        user_info = self._get_user_info(access_token)
        
        if not user_info:
            return Response({
                'success': False,
                'error': 'user_info_failed',
                'error_description': 'Failed to get user information'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if user has access to Mark agent
        if not self._check_mark_access(user_info):
            return Response({
                'success': False,
                'error': 'access_denied',
                'error_description': 'You do not have access to Mark agent'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Create session for user
        self._create_session(request, user_info, access_token)
        
        # Return JSON response with token
        # The frontend will handle the redirect
        return Response({
            'success': True,
            'access_token': access_token,
            'token_type': 'Bearer',
            'user': {
                'user_id': user_info.get('user_id'),
                'email': user_info.get('email'),
                'full_name': user_info.get('full_name'),
                'role': user_info.get('role'),
                'agent_access': user_info.get('agent_access', []),
            }
        })
    
    def _exchange_code_for_token(self, code, state):
        """Exchange authorization code for access token."""
        sia_base_url = getattr(settings, 'SIA_BASE_URL', None)
        mark_frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5174')
        
        if not sia_base_url:
            logger.error("SIA_BASE_URL not configured")
            return None
        
        # The redirect_uri MUST match exactly what was sent during /oauth/authorize/
        redirect_uri = f"{mark_frontend_url.rstrip('/')}/auth/callback"
        
        token_url = f"{sia_base_url}/oauth/token/"
        
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'client_id': getattr(settings, 'SIA_OAUTH_CLIENT_ID', 'mark-agent'),
            'client_secret': getattr(settings, 'SIA_OAUTH_CLIENT_SECRET', ''),
            'redirect_uri': redirect_uri,
        }
        
        # Log token exchange (safe - no sensitive data)
        logger.debug("Exchanging authorization code for token")
        
        try:
            import requests
            response = requests.post(token_url, data=data, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                # Log error without exposing response content (may contain sensitive data)
                logger.error(f"Token exchange failed with status: {response.status_code}")
                return None
                
        except requests.RequestException as e:
            logger.error(f"Token exchange request failed: {e}")
            return None
    
    def _get_user_info(self, access_token):
        """Get user info using access token."""
        try:
            sia_client = get_sia_client()
            profile = sia_client.validate_oauth_token(access_token)
            
            if profile:
                return {
                    'user_id': profile.get('sub'),
                    'email': profile.get('email'),
                    'full_name': profile.get('name'),
                    'tenant_id': profile.get('tenant_id'),
                    'role': profile.get('role', 'user'),
                    'agent_access': profile.get('agent_access', []),
                }
            return None
            
        except Exception as e:
            logger.error(f"Failed to get user info: {e}")
            return None
    
    def _check_mark_access(self, user_info):
        """Check if user has access to Mark agent."""
        agent_access = user_info.get('agent_access', [])
        role = user_info.get('role', 'user')
        
        # Super admin always has access
        if role == 'super_admin':
            return True
        
        # Check if 'mark' is in agent_access
        return 'mark' in agent_access
    
    def _create_session(self, request, user_info, access_token):
        """Create session for authenticated user."""
        request.session['user_id'] = user_info.get('user_id')
        request.session['email'] = user_info.get('email')
        request.session['tenant_id'] = user_info.get('tenant_id')
        request.session['full_name'] = user_info.get('full_name')
        request.session['role'] = user_info.get('role')
        request.session['agent_access'] = user_info.get('agent_access', [])
        request.session['access_token'] = access_token
        request.session['is_authenticated'] = True
        request.session.modified = True
        
        # Log session creation (safe - no email)
        logger.debug(f"Session created for user_id: {user_info.get('user_id', 'unknown')[:8]}...")
    
    def _redirect_with_success(self, redirect_uri, access_token, user_info):
        """Redirect to frontend with success and token."""
        params = {
            'access_token': access_token,
            'token_type': 'Bearer',
        }
        
        # Parse existing URL and add params
        parsed = urlparse(redirect_uri)
        existing_params = parse_qs(parsed.query)
        existing_params.update({k: [v] for k, v in params.items()})
        
        # Rebuild query string
        new_query = urlencode(existing_params, doseq=True)
        
        # Build final URL
        final_url = parsed._replace(query=new_query).geturl()
        
        return HttpResponseRedirect(final_url)
    
    def _redirect_with_error(self, error_code, error_message):
        """Redirect to frontend with error."""
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5174')
        error_path = '/auth/callback'
        
        params = {
            'error': error_code,
            'error_description': error_message,
        }
        
        redirect_url = f"{frontend_url.rstrip('/')}{error_path}?{urlencode(params)}"
        return HttpResponseRedirect(redirect_url)


class OAuthStatusView(APIView):
    """
    Check OAuth session status.
    
    Returns the current authentication status and user info from session.
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        tags=['Authentication'],
        summary='Check OAuth Session Status',
        description='''
        Check the current OAuth session status.
        
        Returns:
        - `authenticated`: Whether user is authenticated
        - `user`: User information (if authenticated)
        - `session_expires`: Session expiration time (if applicable)
        ''',
        responses={
            200: OpenApiResponse(
                description='Session status',
                response={
                    'type': 'object',
                    'properties': {
                        'authenticated': {'type': 'boolean'},
                        'user': {
                            'type': 'object',
                            'properties': {
                                'user_id': {'type': 'string'},
                                'email': {'type': 'string'},
                                'full_name': {'type': 'string'},
                                'tenant_id': {'type': 'string'},
                                'role': {'type': 'string'},
                                'agent_access': {'type': 'array', 'items': {'type': 'string'}},
                            }
                        },
                    }
                }
            )
        }
    )
    def get(self, request):
        is_authenticated = request.session.get('is_authenticated', False)
        
        if not is_authenticated:
            return Response({
                'authenticated': False,
                'message': 'No active session'
            })
        
        return Response({
            'authenticated': True,
            'user': {
                'user_id': request.session.get('user_id'),
                'email': request.session.get('email'),
                'full_name': request.session.get('full_name'),
                'tenant_id': request.session.get('tenant_id'),
                'role': request.session.get('role'),
                'agent_access': request.session.get('agent_access', []),
            },
            'token_info': {
                'has_access_token': bool(request.session.get('access_token')),
            }
        })


class OAuthLogoutView(APIView):
    """
    Logout and clear session.
    
    Clears the Django session and optionally revokes the token with SIA.
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        tags=['Authentication'],
        summary='Logout',
        description='''
        Logout and clear the current session.
        
        This clears the Django session. Optionally redirects to a logout page.
        
        Query Parameters:
        - `redirect_uri`: Where to redirect after logout (optional)
        ''',
        parameters=[
            OpenApiParameter(
                name='redirect_uri',
                type=str,
                location=OpenApiParameter.QUERY,
                description='URL to redirect after logout',
                required=False
            ),
        ],
        responses={
            200: OpenApiResponse(description='Logged out successfully'),
            302: OpenApiResponse(description='Redirected to specified URL')
        }
    )
    def post(self, request):
        request.session.flush()
        
        redirect_uri = request.query_params.get('redirect_uri')
        
        if redirect_uri:
            return HttpResponseRedirect(redirect_uri)
        
        return Response({
            'success': True,
            'message': 'Logged out successfully'
        })
    
    def get(self, request):
        """Allow GET for simple logout links."""
        return self.post(request)


class SSOLoginView(APIView):
    """
    SSO Login for users already authenticated with SIA.
    
    This endpoint accepts a JWT token from SIA frontend and creates a session.
    Used when user is already logged into SIA and clicks on Mark Agent.
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        tags=['Authentication'],
        summary='SSO Login with JWT Token',
        description='''
        SSO login for users already authenticated with SIA.
        
        This endpoint accepts a valid SIA JWT token and creates a session.
        Used when user is already logged into SIA and clicks on Mark Agent.
        
        The token should be obtained from SIA backend after login.
        
        **Request Body:**
        ```json
        {
            "token": "eyJhbGciOiJIUzI1NiIs...",
            "redirect_uri": "http://localhost:3000/dashboard"
        }
        ```
        
        **Response:**
        - Success: Redirects to redirect_uri with session info
        - Failure: Returns 401 with error details
        ''',
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'token': {
                        'type': 'string',
                        'description': 'SIA JWT token'
                    },
                    'redirect_uri': {
                        'type': 'string',
                        'description': 'Where to redirect after login'
                    }
                },
                'required': ['token']
            }
        },
        responses={
            200: OpenApiResponse(
                description='Login successful',
                response={
                    'type': 'object',
                    'properties': {
                        'success': {'type': 'boolean'},
                        'user': {'type': 'object'},
                        'redirect_url': {'type': 'string'}
                    }
                }
            ),
            302: OpenApiResponse(description='Redirects to frontend'),
            401: OpenApiResponse(description='Invalid token or no access'),
        }
    )
    def post(self, request):
        token = request.data.get('token')
        redirect_uri = request.data.get(
            'redirect_uri',
            getattr(settings, 'FRONTEND_URL', 'http://localhost:5174')
        )
        
        if not token:
            return Response(
                {'error': 'Token is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate token with SIA
        try:
            sia_client = get_sia_client()
            profile = sia_client.get_user_profile(token)
            
            if not profile:
                return Response(
                    {'error': 'Invalid token'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Check Mark access
            agent_access = profile.get('agent_access', [])
            role = profile.get('role', 'user')
            
            if 'mark' not in agent_access and role != 'super_admin':
                return Response(
                    {'error': 'Access denied - Mark agent not available'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Create session
            request.session['user_id'] = profile.get('user_id')
            request.session['email'] = profile.get('email')
            request.session['tenant_id'] = profile.get('tenant_id')
            request.session['full_name'] = profile.get('full_name')
            request.session['role'] = profile.get('role')
            request.session['agent_access'] = agent_access
            request.session['access_token'] = token
            request.session['is_authenticated'] = True
            request.session.modified = True
            
            # Log successful SSO (safe)
            logger.info(f"SSO login successful for user_id: {profile.get('user_id', 'unknown')[:8]}...")
            
            # If redirect_uri provided, return it in response
            if request.data.get('redirect_uri'):
                return Response({
                    'success': True,
                    'user': {
                        'user_id': profile.get('user_id'),
                        'email': profile.get('email'),
                        'full_name': profile.get('full_name'),
                        'tenant_id': profile.get('tenant_id'),
                        'role': profile.get('role'),
                        'agent_access': agent_access,
                    },
                    'redirect_url': redirect_uri
                })
            
            # Otherwise redirect directly
            return HttpResponseRedirect(redirect_uri)
            
        except Exception as e:
            logger.error(f"SSO login failed: {e}")
            return Response(
                {'error': 'Authentication failed'},
                status=status.HTTP_401_UNAUTHORIZED
            )


def datetime_now():
    """Helper to get current datetime as string."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
