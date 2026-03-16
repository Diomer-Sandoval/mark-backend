def check_ownership(obj, user):
    """
    Check if user owns this object or is super admin.
    
    Compatible with objects having 'user_id' or 'tenant_id'.
    Supports hierarchical checks for Creations and Generations.
    """
    if not user:
        return False
        
    # Service user (API Key) bypasses checks if configured
    if hasattr(user, 'user_id') and user.user_id == 'service':
        return True
        
    # Direct ownership
    if hasattr(obj, 'user_id') and obj.user_id == getattr(user, 'user_id', None):
        return True
        
    # Tenant ownership
    if hasattr(obj, 'tenant_id') and getattr(user, 'tenant_id', None) and obj.tenant_id == user.tenant_id:
        return True
    
    # Hierarchical checks (Import inside to avoid circular deps)
    from creation_studio.models import Creation, Generation
    from platform_insights.models import PlatformInsight, Post
    
    if isinstance(obj, Creation) and obj.brand:
        return check_ownership(obj.brand, user)
    if isinstance(obj, Generation) and obj.creation:
        return check_ownership(obj.creation, user)
    if isinstance(obj, PlatformInsight) and obj.brand:
        return check_ownership(obj.brand, user)
    if isinstance(obj, Post) and obj.brand:
        return check_ownership(obj.brand, user)
        
    return False
