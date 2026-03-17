"""
Authentication utilities for SIA Solutions integration.

Supports two authentication methods:
1. JWT Bearer token (from SIA Solutions)
2. API Key (for service-to-service communication)
"""

import os
import jwt
import base64
import json
import requests
import logging
from functools import wraps
from datetime import datetime, timezone
from django.conf import settings
from rest_framework import authentication, exceptions
from rest_framework.request import Request

logger = logging.getLogger(__name__)


def decode_jwt_without_verification(token):
    """
    Decode JWT token without signature verification.
    Used when we don't have the JWT secret.
    """
    try:
        # Split the token
        parts = token.split('.')
        if len(parts) != 3:
            return None, "Invalid JWT format"

        # Decode payload
        payload_padding = '=' * (4 - len(parts[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(parts[1] + payload_padding))

        return payload, None
    except Exception as e:
        return None, str(e)


class SIAUser:
    """
    Simple user-like object for DRF compatibility.
    Represents an authenticated SIA Solutions user.
    """

    def __init__(self, user_id, email, tenant_id=None, full_name=None,
                 role='user', agent_access=None):
        self.user_id = user_id
        self.email = email
        self.tenant_id = tenant_id
        self.full_name = full_name
        self.role = role
        self.agent_access = agent_access or []

        # DRF compatibility
        self.is_authenticated = True
        self.is_anonymous = False
        self.is_active = True

    def __str__(self):
        return f"{self.email} ({self.user_id})"

    @property
    def can_access_mark(self):
        """Check if user can access Mark agent."""
        return 'mark' in self.agent_access or self.role == 'super_admin'


class SIAJWTAuthentication(authentication.BaseAuthentication):
    """
    Authenticate requests using SIA Solutions JWT tokens.

    Expected header: Authorization: Bearer <jwt_token>

    The JWT should contain:
    - sub: user_id (supabase_uid)
    - email: user email
    - tenant_id: tenant UUID
    - agent_access: list of accessible agents
    """

    keyword = 'Bearer'

    def authenticate(self, request: Request):
        auth_header = authentication.get_authorization_header(request).split()

        if not auth_header or auth_header[0].lower() != self.keyword.lower().encode():
            return None

        if len(auth_header) == 1:
            msg = 'Invalid token header. No credentials provided.'
            raise exceptions.AuthenticationFailed(msg)
        elif len(auth_header) > 2:
            msg = 'Invalid token header. Token string should not contain spaces.'
            raise exceptions.AuthenticationFailed(msg)

        try:
            token = auth_header[1].decode('utf-8')
        except UnicodeError:
            msg = 'Invalid token header. Token string should not contain invalid characters.'
            raise exceptions.AuthenticationFailed(msg)

        return self.authenticate_credentials(token)

    def authenticate_credentials(self, token):
        """
        Validate JWT token and return user.
        """
        # Decode without verification using base64
        payload, error = decode_jwt_without_verification(token)

        if payload:
            # Check if token is expired
            exp = payload.get('exp')
            if exp:
                if datetime.now(timezone.utc).timestamp() > exp:
                    raise exceptions.AuthenticationFailed('Token has expired.')

            user = self._create_user_from_payload(payload, token)
            return (user, token)

        # Method 2: Try local validation if JWT_SECRET is configured
        jwt_secret = getattr(settings, 'SIA_JWT_SECRET', None) or os.getenv('SIA_JWT_SECRET')

        if jwt_secret:
            try:
                payload = jwt.decode(token, jwt_secret, algorithms=['HS256'])
                user = self._create_user_from_payload(payload, token)
                return (user, token)
            except jwt.ExpiredSignatureError:
                raise exceptions.AuthenticationFailed('Token has expired.')
            except jwt.InvalidTokenError:
                pass  # Fall through to remote validation

        # Method 3: Remote validation via SIA Solutions
        return self._validate_with_sia(token)

    def _create_user_from_payload(self, payload, token=None):
        """Create SIAUser from JWT payload.

        Handles different payload formats from SIA Solutions.
        If tenant_id or agent_access is missing, fetches from SIA backend.
        """
        # Extract user ID - could be 'sub', 'user_id', or 'id'
        user_id = payload.get('sub') or payload.get('user_id') or payload.get('id')

        # Extract email
        email = payload.get('email') or payload.get('user_email') or 'unknown@example.com'

        # Extract tenant ID - could be in different formats
        tenant_id = payload.get('tenant_id') or payload.get('tenant')

        # Handle nested tenant object
        if isinstance(tenant_id, dict):
            tenant_id = tenant_id.get('id') or tenant_id.get('tenant_id')

        # Extract full name
        full_name = payload.get('full_name') or payload.get('name')

        # Extract role
        role = payload.get('role') or payload.get('user_role', 'user')

        # Extract agent access - could be array or string
        agent_access = payload.get('agent_access', [])
        if isinstance(agent_access, str):
            agent_access = [agent_access]

        # Also check app_metadata or user_metadata (Supabase format)
        if not agent_access and 'app_metadata' in payload:
            agent_access = payload['app_metadata'].get('agent_access', [])

        if not tenant_id and 'app_metadata' in payload:
            tenant_id = payload['app_metadata'].get('tenant_id')

        # If we still don't have tenant_id or agent_access, fetch from SIA
        if (not tenant_id or not agent_access) and token:
            try:
                from .client import get_sia_client
                sia = get_sia_client()
                sia_profile = sia.get_user_profile(token)

                if sia_profile:
                    tenant_id = sia_profile.get('tenant_id') or tenant_id
                    agent_access = sia_profile.get('agent_access', []) or agent_access
                    full_name = sia_profile.get('full_name') or full_name or sia_profile.get('name')
                    role = sia_profile.get('role') or role
            except Exception as e:
                logger.warning(f"Failed to fetch SIA profile: {e}")

        return SIAUser(
            user_id=user_id,
            email=email,
            tenant_id=tenant_id,
            full_name=full_name,
            role=role,
            agent_access=agent_access
        )

    def _validate_with_sia(self, token):
        """
        Validate token with SIA Solutions userinfo endpoint.

        Endpoint: GET /oauth/userinfo/
        Header: Authorization: Bearer <access_token>
        """
        sia_base_url = getattr(settings, 'SIA_BASE_URL', None) or os.getenv('SIA_BASE_URL')

        if not sia_base_url:
            raise exceptions.AuthenticationFailed(
                'SIA_BASE_URL not configured. Cannot validate token.'
            )

        try:
            response = requests.get(
                f"{sia_base_url}/oauth/userinfo/",
                headers={'Authorization': f'Bearer {token}'},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                user = SIAUser(
                    user_id=data.get('sub'),
                    email=data.get('email'),
                    tenant_id=data.get('tenant_id'),
                    full_name=data.get('name'),
                    role=data.get('role', 'user'),
                    agent_access=data.get('agent_access', [])
                )
                return (user, token)
            elif response.status_code == 401:
                raise exceptions.AuthenticationFailed('Invalid or expired token.')
            else:
                raise exceptions.AuthenticationFailed(
                    f'SIA authentication service error: {response.status_code}'
                )
        except requests.RequestException as e:
            raise exceptions.AuthenticationFailed(
                f'Could not connect to SIA authentication service: {str(e)}'
            )


class SIAAPIKeyAuthentication(authentication.BaseAuthentication):
    """
    Authenticate using API keys for service-to-service communication.

    Expected header: X-API-Key: <api_key>
    """

    def authenticate(self, request: Request):
        api_key = request.headers.get('X-API-Key')

        if not api_key:
            return None

        return self.authenticate_credentials(api_key)

    def authenticate_credentials(self, api_key):
        """
        Validate API key.

        For now, we accept any key starting with 'sia_' as valid
        (in production, this should validate against SIA Solutions)
        """
        if not api_key.startswith('sia_'):
            raise exceptions.AuthenticationFailed('Invalid API key format.')

        # In production, validate against SIA Solutions
        # For now, create a service user
        user = SIAUser(
            user_id='service',
            email='service@sia-solutions.com',
            tenant_id=None,
            role='service',
            agent_access=['mark']
        )

        return (user, api_key)


class AllowUnauthenticated(authentication.BaseAuthentication):
    """
    Allow unauthenticated requests.

    Returns an anonymous user that allows the request to proceed.
    Use this for public endpoints.
    """

    def authenticate(self, request):
        return None


class SIASessionAuthentication(authentication.BaseAuthentication):
    """
    Authenticate using Django session (for OAuth web flow).
    
    This authentication class checks if user is authenticated via Django session
    after OAuth login. Used for web browser clients that have gone through
    the OAuth flow.
    
    Expected: Valid Django session with user_id stored from OAuth.
    """
    
    def authenticate(self, request: Request):
        # Check if session has user data from OAuth
        if not request.session.get('is_authenticated'):
            return None
        
        user_id = request.session.get('user_id')
        if not user_id:
            return None
        
        # Create SIAUser from session data
        user = SIAUser(
            user_id=user_id,
            email=request.session.get('email', ''),
            tenant_id=request.session.get('tenant_id'),
            full_name=request.session.get('full_name'),
            role=request.session.get('role', 'user'),
            agent_access=request.session.get('agent_access', [])
        )
        
        # Get access token from session if available
        token = request.session.get('access_token', 'session')
        
        return (user, token)


def get_current_user(request):
    """
    Helper to get the current authenticated user from request.

    Returns SIAUser or None if not authenticated.
    """
    user = getattr(request, 'user', None)
    if user and hasattr(user, 'is_authenticated') and user.is_authenticated:
        return user
        
    # Support development mode without authentication
    if getattr(settings, 'DEV_MODE_ALLOW_UNAUTHENTICATED', False):
        return SIAUser(
            user_id='service',
            email='dev@example.com',
            role='super_admin',
            agent_access=['mark']
        )
        
    return None


def require_auth(permission_check=None):
    """
    Decorator to require authentication for a view.

    Args:
        permission_check: Optional function(user) -> bool to check permissions
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user = get_current_user(request)

            if not user:
                raise exceptions.AuthenticationFailed('Authentication required.')

            if permission_check and not permission_check(user):
                raise exceptions.PermissionDenied('Permission denied.')

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


# Permission check functions

def can_access_mark(user):
    """Check if user can access Mark agent."""
    return getattr(user, 'can_access_mark', False) or getattr(user, 'is_super_admin', False)


def is_super_admin(user):
    """Check if user is super admin."""
    return getattr(user, 'role', None) == 'super_admin'
