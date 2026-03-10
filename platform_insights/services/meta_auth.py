"""
Meta API Authentication configuration.

Credentials should be loaded from environment variables using python-dotenv 
rather than hardcoded to prevent accidental commits to the repository.
"""
import os
from dotenv import load_dotenv

# Ensure environment variables from .env are loaded
load_dotenv()

META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN") or os.getenv("META_FB_ACCESS_TOKEN", "")

INSTAGRAM_BUSINESS_ACCOUNT_ID = os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID", "")
FACEBOOK_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID", "")
