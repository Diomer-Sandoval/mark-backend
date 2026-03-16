"""
OpenAPI Schema Extensions for drf-spectacular.

This module provides custom extensions for documenting authentication
and other custom features in the OpenAPI schema.
"""

from drf_spectacular.extensions import OpenApiAuthenticationExtension
from drf_spectacular.plumbing import build_bearer_security_scheme_object


class SIAJWTAuthenticationExtension(OpenApiAuthenticationExtension):
    """
    OpenAPI extension for SIA JWT Authentication.

    Documents the Bearer token authentication in Swagger UI.
    """
    target_class = 'authentication.backends.SIAJWTAuthentication'
    name = 'SIA JWT Auth'

    def get_security_definition(self, auto_schema):
        schema = build_bearer_security_scheme_object(
            header_name='Authorization',
            token_prefix='Bearer',
        )
        schema['description'] = 'SIA Solutions JWT token. Obtain from SIA Solutions login endpoint.'
        return schema


class SIAAPIKeyAuthenticationExtension(OpenApiAuthenticationExtension):
    """
    OpenAPI extension for SIA API Key Authentication.

    Documents the API key authentication in Swagger UI.
    """
    target_class = 'authentication.backends.SIAAPIKeyAuthentication'
    name = 'SIA API Key'

    def get_security_definition(self, auto_schema):
        return {
            'type': 'apiKey',
            'in': 'header',
            'name': 'X-API-Key',
            'description': 'SIA Solutions API key for service-to-service authentication. Format: sia_<32-char-random>_<16-char-urlsafe>'
        }
