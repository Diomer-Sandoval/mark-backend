"""
Debug authentication - shows what the token contains.
"""

import jwt
import base64
import json


def decode_token_debug(token):
    """Decode JWT token without verification to see its contents."""
    try:
        # Remove 'Bearer ' prefix if present
        if token.startswith('Bearer '):
            token = token[7:]
        
        # Split the token
        parts = token.split('.')
        if len(parts) != 3:
            return {"error": "Invalid JWT format - should have 3 parts"}
        
        # Decode header
        header_padding = '=' * (4 - len(parts[0]) % 4)
        header = json.loads(base64.urlsafe_b64decode(parts[0] + header_padding))
        
        # Decode payload
        payload_padding = '=' * (4 - len(parts[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(parts[1] + payload_padding))
        
        return {
            "header": header,
            "payload": payload,
            "valid_format": True
        }
    except Exception as e:
        return {"error": str(e)}


def extract_user_from_token(token):
    """Extract user info from SIA token."""
    debug_info = decode_token_debug(token)
    
    if "error" in debug_info:
        return debug_info
    
    payload = debug_info["payload"]
    
    # Try to find user info in various formats
    user_info = {
        "user_id": payload.get("sub") or payload.get("user_id") or payload.get("id"),
        "email": payload.get("email") or payload.get("user_email"),
        "tenant_id": payload.get("tenant_id") or payload.get("tenant"),
        "role": payload.get("role") or payload.get("user_role", "user"),
        "agent_access": payload.get("agent_access", []),
    }
    
    # Check app_metadata (Supabase format)
    if "app_metadata" in payload:
        app_meta = payload["app_metadata"]
        if not user_info["tenant_id"]:
            user_info["tenant_id"] = app_meta.get("tenant_id")
        if not user_info["agent_access"]:
            user_info["agent_access"] = app_meta.get("agent_access", [])
    
    # Check user_metadata
    if "user_metadata" in payload:
        user_meta = payload["user_metadata"]
        if not user_info["email"]:
            user_info["email"] = user_meta.get("email")
    
    return {
        "user_info": user_info,
        "full_payload": payload
    }
