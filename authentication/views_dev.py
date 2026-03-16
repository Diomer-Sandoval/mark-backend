"""
Test utilities for development and Swagger UI testing.
"""

import uuid
from datetime import datetime, timezone, timedelta
from django.conf import settings
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample

from .debug import decode_token_debug, extract_user_from_token
from .backends import SIAJWTAuthentication, SIAAPIKeyAuthentication


class TestTokenView(APIView):
    """
    Generate a test JWT token for Swagger UI testing.

    WARNING: This endpoint is for DEVELOPMENT ONLY.
    Do not enable in production!
    """
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Development'],
        summary='Generate Test JWT Token',
        description='''
        Generate a test JWT token for development testing.

        **WARNING**: This endpoint is for DEVELOPMENT ONLY.

        Use this token in Swagger UI:
        1. Click "Authorize" button
        2. In "SIA JWT Auth" section, enter: `Bearer <token>`
        3. Click "Authorize" and "Close"

        The generated token will be associated with dummy user data.
        ''',
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'user_id': {'type': 'string', 'description': 'User UUID'},
                    'email': {'type': 'string', 'description': 'User email'},
                    'tenant_id': {'type': 'string', 'description': 'Tenant UUID'},
                }
            }
        },
        responses={
            200: OpenApiResponse(
                description='Test token generated',
                response={
                    'type': 'object',
                    'properties': {
                        'token': {'type': 'string'},
                        'user': {'type': 'object'},
                        'expires_in': {'type': 'integer'},
                    }
                }
            ),
            403: OpenApiResponse(description='Not in development mode')
        },
        examples=[
            OpenApiExample(
                'Test Token Request',
                value={
                    'user_id': '550e8400-e29b-41d4-a716-446655440000',
                    'email': 'test@example.com',
                    'tenant_id': '660e8400-e29b-41d4-a716-446655440000'
                },
                request_only=True
            ),
            OpenApiExample(
                'Test Token Response',
                value={
                    'token': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
                    'user': {
                        'user_id': '550e8400-e29b-41d4-a716-446655440000',
                        'email': 'test@example.com',
                        'tenant_id': '660e8400-e29b-41d4-a716-446655440000',
                        'role': 'user',
                        'agent_access': ['mark']
                    },
                    'expires_in': 3600,
                    'usage': 'Use this token in Swagger: Authorization: Bearer <token>'
                },
                response_only=True,
                status_codes=['200']
            )
        ]
    )
    def post(self, request):
        # Get or create test user data
        user_id = request.data.get('user_id', str(uuid.uuid4()))
        email = request.data.get('email', 'test@example.com')
        tenant_id = request.data.get('tenant_id', str(uuid.uuid4()))

        # Create JWT payload
        payload = {
            'sub': user_id,
            'email': email,
            'tenant_id': tenant_id,
            'role': 'user',
            'agent_access': ['mark'],
            'iat': datetime.now(timezone.utc),
            'exp': datetime.now(timezone.utc) + timedelta(hours=1),
            'type': 'test_token'
        }

        # Generate token
        try:
            import jwt
            # Use a test secret
            test_secret = settings.SECRET_KEY[:32]
            token = jwt.encode(payload, test_secret, algorithm='HS256')

            return Response({
                'token': token,
                'user': {
                    'user_id': user_id,
                    'email': email,
                    'tenant_id': tenant_id,
                    'role': 'user',
                    'agent_access': ['mark']
                },
                'expires_in': 3600,
                'usage': 'Use this token in Swagger: Authorization: Bearer <token>'
            })
        except Exception as e:
            return Response(
                {'error': f'Failed to generate token: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AuthStatusView(APIView):
    """
    Check current authentication status.

    Returns information about the currently authenticated user.
    """
    # Require authentication to check status
    authentication_classes = [SIAJWTAuthentication, SIAAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Development'],
        summary='Check Auth Status',
        description='Returns information about the currently authenticated user.',
        responses={
            200: OpenApiResponse(description='Auth status'),
            401: OpenApiResponse(description='Not authenticated')
        }
    )
    def get(self, request):
        from .backends import get_current_user

        # Get the Authorization header
        auth_header = request.headers.get('Authorization', '')

        user = get_current_user(request)

        if not user:
            # Try to decode the token for debugging
            debug_info = None
            if auth_header.startswith('Bearer '):
                token = auth_header[7:]
                debug_info = extract_user_from_token(token)

            return Response({
                'authenticated': False,
                'message': 'No authentication provided',
                'auth_header_present': bool(auth_header),
                'auth_header_prefix': auth_header[:20] + '...' if auth_header else None,
                'token_debug': debug_info
            }, status=status.HTTP_200_OK)  # Return 200 for debugging

        return Response({
            'authenticated': True,
            'user': {
                'user_id': getattr(user, 'user_id', None),
                'email': getattr(user, 'email', None),
                'tenant_id': getattr(user, 'tenant_id', None),
                'role': getattr(user, 'role', None),
                'agent_access': getattr(user, 'agent_access', []),
            }
        })


class TestSIAConnectionView(APIView):
    """
    Test SIA backend connection.

    Directly calls SIA /api/auth/profile/ endpoint to verify connectivity.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Development'],
        summary='Test SIA Connection',
        description='Tests the connection to SIA backend /api/auth/profile/ endpoint.',
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'token': {'type': 'string', 'description': 'JWT token to test'},
                },
                'required': ['token']
            }
        },
        responses={
            200: OpenApiResponse(description='SIA response'),
            400: OpenApiResponse(description='Error')
        }
    )
    def post(self, request):
        token = request.data.get('token', '')

        if not token:
            return Response(
                {'error': 'No token provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Remove Bearer prefix if present
        if token.startswith('Bearer '):
            token = token[7:]

        try:
            import requests
            from django.conf import settings

            sia_base_url = getattr(settings, 'SIA_BASE_URL', 'http://127.0.0.1:8001')
            endpoint = f"{sia_base_url}/api/auth/profile/"

            response = requests.get(
                endpoint,
                headers={
                    'Authorization': f'Bearer {token}',
                    'Content-Type': 'application/json'
                },
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()

                # Extract user data from SIA response
                if 'data' in data:
                    user_data = data['data']
                    tenant = user_data.get('tenant', {})

                    return Response({
                        'sia_base_url': sia_base_url,
                        'endpoint': endpoint,
                        'raw_response': data,
                        'extracted_profile': {
                            'user_id': user_data.get('id'),
                            'email': user_data.get('email'),
                            'full_name': user_data.get('full_name'),
                            'tenant_id': tenant.get('id') if isinstance(tenant, dict) else None,
                            'tenant_name': tenant.get('name') if isinstance(tenant, dict) else None,
                            'role': user_data.get('role'),
                            'agent_access': user_data.get('accessible_agents', []),
                            'can_access_mark': user_data.get('can_access_mark', False),
                            'can_access_hr': user_data.get('can_access_hr', False),
                        },
                        'has_tenant': tenant.get('id') is not None if isinstance(tenant, dict) else False,
                        'has_agent_access': bool(user_data.get('accessible_agents', [])),
                        'can_access_mark': user_data.get('can_access_mark', False),
                    })
                else:
                    return Response({
                        'sia_base_url': sia_base_url,
                        'endpoint': endpoint,
                        'raw_response': data,
                        'warning': 'Unexpected response format - no "data" key'
                    })
            else:
                return Response({
                    'sia_base_url': sia_base_url,
                    'endpoint': endpoint,
                    'error': f'SIA returned {response.status_code}',
                    'response_body': response.text
                }, status=response.status_code)

        except Exception as e:
            import traceback
            return Response({
                'error': str(e),
                'traceback': traceback.format_exc()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DebugTokenView(APIView):
    """
    Debug endpoint to decode a JWT token.

    Shows what's inside the token without verifying signature.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Development'],
        summary='Debug JWT Token',
        description='Decodes a JWT token to show its contents without verification.',
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'token': {'type': 'string', 'description': 'JWT token to decode'},
                },
                'required': ['token']
            }
        },
        responses={
            200: OpenApiResponse(description='Token decoded'),
            400: OpenApiResponse(description='Invalid token')
        }
    )
    def post(self, request):
        token = request.data.get('token', '')

        if not token:
            return Response(
                {'error': 'No token provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Remove Bearer prefix if present
        if token.startswith('Bearer '):
            token = token[7:]

        result = extract_user_from_token(token)

        return Response(result)
