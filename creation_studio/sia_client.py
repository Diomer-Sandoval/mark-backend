"""
SIA Solutions API Client.

This module provides a client for communicating with the SIA backend
to fetch user profiles, verify tokens, and get tenant information.
"""

import os
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class SIAClient:
    """
    Client for SIA Solutions backend API.
    """
    
    def __init__(self, base_url=None):
        self.base_url = base_url or getattr(settings, 'SIA_BASE_URL', None) or os.getenv('SIA_BASE_URL')
        if not self.base_url:
            raise ValueError("SIA_BASE_URL not configured")
    
    def get_user_profile(self, jwt_token):
        """
        Fetch user profile from SIA backend using Supabase JWT token.
        
        This endpoint requires a valid Supabase JWT token (not OAuth token).
        The user must be logged into SIA and provide their JWT.
        
        Endpoint: GET /api/auth/profile/
        Headers: Authorization: Bearer <supabase_jwt_token>
        
        Returns:
            dict: User profile with tenant_id, agent_access, etc.
            None: If request fails
        """
        endpoint = f"{self.base_url}/api/auth/profile/"
        
        try:
            response = requests.get(
                endpoint,
                headers={
                    'Authorization': f'Bearer {jwt_token}',
                    'Content-Type': 'application/json'
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Handle wrapped response (SIA wraps in 'data' key)
                if 'data' in data and isinstance(data['data'], dict):
                    user_data = data['data']
                    tenant_info = user_data.get('tenant', {})
                    
                    return {
                        'user_id': user_data.get('id'),
                        'email': user_data.get('email'),
                        'full_name': user_data.get('full_name'),
                        'tenant_id': tenant_info.get('id') if isinstance(tenant_info, dict) else None,
                        'tenant_name': tenant_info.get('name') if isinstance(tenant_info, dict) else None,
                        'role': user_data.get('role'),
                        'agent_access': user_data.get('accessible_agents', []),
                        'can_access_mark': user_data.get('can_access_mark', False),
                        'can_access_hr': user_data.get('can_access_hr', False),
                    }
                return None
            else:
                logger.warning(f"SIA API error: {response.status_code}")
                return None
                
        except requests.RequestException as e:
            logger.error(f"SIA request failed: {e}")
            return None
    
    def validate_oauth_token(self, access_token):
        """
        Validate OAuth access token and get user info.
        
        Use this for OAuth-based authentication flow.
        Endpoint: GET /oauth/userinfo/
        
        Returns:
            dict: User profile from OAuth token
            None: If token invalid
        """
        endpoint = f"{self.base_url}/oauth/userinfo/"
        
        try:
            response = requests.get(
                endpoint,
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                },
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            return None
            
        except requests.RequestException as e:
            logger.error(f"SIA OAuth request failed: {e}")
            return None
    
    def validate_token(self, jwt_token):
        """
        Validate a JWT token with SIA backend.
        
        Returns:
            dict: Token validation result with user info
            None: If token is invalid
        """
        # Try to get user profile - this validates the token
        profile = self.get_user_profile(jwt_token)
        return profile
    
    def get_user_by_id(self, user_id, admin_token):
        """
        Get user by ID (requires admin token).
        
        Endpoint: GET /api/auth/admin/users/{user_id}/
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/auth/admin/users/{user_id}/",
                headers={
                    'Authorization': f'Bearer {admin_token}',
                    'Content-Type': 'application/json'
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data:
                    return data['data']
                return data
            return None
            
        except requests.RequestException as e:
            logger.error(f"SIA request failed: {e}")
            return None


# Global client instance
_sia_client = None


def get_sia_client():
    """Get or create SIA client instance."""
    global _sia_client
    if _sia_client is None:
        _sia_client = SIAClient()
    return _sia_client
