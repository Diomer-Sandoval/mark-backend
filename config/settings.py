"""
Django settings for mark-backend project.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/6.0/ref/settings/
"""

from pathlib import Path
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# =============================================================================
# SECURITY SETTINGS
# =============================================================================

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-dev-key-change-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DJANGO_DEBUG', 'True').lower() == 'true'

ALLOWED_HOSTS = os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')


# =============================================================================
# APPLICATION DEFINITION
# =============================================================================

INSTALLED_APPS = [
    'corsheaders',
    'creation_studio',
    'brand_dna_extractor',
    'rest_framework',
    'drf_spectacular',
    'corsheaders',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# =============================================================================
# DATABASE
# =============================================================================

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# =============================================================================
# PASSWORD VALIDATION
# =============================================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# =============================================================================
# INTERNATIONALIZATION
# =============================================================================

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# =============================================================================
# STATIC FILES
# =============================================================================

STATIC_URL = 'static/'


# =============================================================================
# DEFAULT PRIMARY KEY FIELD TYPE
# =============================================================================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# =============================================================================
# DJANGO REST FRAMEWORK CONFIGURATION
# =============================================================================

# CORS
CORS_ALLOWED_ORIGINS = [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
]

# Django REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'creation_studio.authentication.SIAJWTAuthentication',
        'creation_studio.authentication.SIAAPIKeyAuthentication',
        'creation_studio.authentication.SIASessionAuthentication',
    ],
}

# Development mode - set to True to allow testing without authentication
DEV_MODE_ALLOW_UNAUTHENTICATED = os.getenv('DEV_MODE_ALLOW_UNAUTHENTICATED', 'False').lower() == 'true'

if DEV_MODE_ALLOW_UNAUTHENTICATED:
    REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES'] = ['rest_framework.permissions.AllowAny']
    REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'] = []


# =============================================================================
# SIA SOLUTIONS INTEGRATION
# =============================================================================

# SIA Backend URL (the actual API server)
SIA_BASE_URL = os.getenv('SIA_BASE_URL', 'https://sia-backend-sbw7.onrender.com')

# SIA Frontend URL (the landing page - for OAuth redirect)
SIA_FRONTEND_URL = os.getenv('SIA_FRONTEND_URL', 'http://localhost:3000')

# JWT Secret for local validation (optional)
SIA_JWT_SECRET = os.getenv('SIA_JWT_SECRET', None)


# =============================================================================
# OAUTH 2.0 CONFIGURATION
# =============================================================================

# OAuth client credentials (from SIA backend)
SIA_OAUTH_CLIENT_ID = os.getenv('SIA_OAUTH_CLIENT_ID', 'mark-agent')
SIA_OAUTH_CLIENT_SECRET = os.getenv('SIA_OAUTH_CLIENT_SECRET', '')


# =============================================================================
# MARK FRONTEND CONFIGURATION
# =============================================================================

# Mark Frontend URL (where users are redirected after OAuth)
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:5174')

# OAuth error page path
OAUTH_ERROR_PATH = os.getenv('OAUTH_ERROR_PATH', '/auth/error')

# Include user info in OAuth redirect
OAUTH_INCLUDE_USER_INFO = os.getenv('OAUTH_INCLUDE_USER_INFO', 'False').lower() == 'true'


# =============================================================================
# OPENAI CONFIGURATION
# =============================================================================

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', None)


# =============================================================================
# SESSION CONFIGURATION (FOR OAUTH)
# =============================================================================

SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = int(os.getenv('SESSION_COOKIE_AGE', '3600'))  # 1 hour
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG  # Secure in production
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_SAVE_EVERY_REQUEST = True


# =============================================================================
# CACHE CONFIGURATION (FOR OAUTH STATE)
# =============================================================================

# Use database cache for persistence across server restarts
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'django_cache',
    }
}


# =============================================================================
# CORS CONFIGURATION
# =============================================================================

# Parse CORS origins from environment variable
# Format: comma-separated list of origins
# Example: CORS_ALLOWED_ORIGINS=http://localhost:5174,http://localhost:3000
_cors_origins = os.getenv('CORS_ALLOWED_ORIGINS', 'http://localhost:5174,http://localhost:3000')
CORS_ALLOWED_ORIGINS = [origin.strip() for origin in _cors_origins.split(',') if origin.strip()]

# Allow credentials (cookies, authorization headers)
CORS_ALLOW_CREDENTIALS = os.getenv('CORS_ALLOW_CREDENTIALS', 'True').lower() == 'true'

# Allow all common HTTP methods
CORS_ALLOW_METHODS = [
    'GET',
    'POST',
    'PUT',
    'PATCH',
    'DELETE',
    'OPTIONS',
]

# Allow all common headers
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]


# =============================================================================
# DRF-SPECTACULAR CONFIGURATION (SWAGGER/OPENAPI)
# =============================================================================

SPECTACULAR_SETTINGS = {
    # Custom authentication extensions
    'AUTHENTICATION_EXTENSIONS': [
        'creation_studio.schema_extensions.SIAJWTAuthenticationExtension',
        'creation_studio.schema_extensions.SIAAPIKeyAuthenticationExtension',
    ],
    'TITLE': 'Mark Backend - Marketing Agent API',
    'DESCRIPTION': '''
    # Mark Backend API Documentation

    This API provides AI-powered marketing content creation and brand management capabilities.

    ## Key Features:
    - **Brand Management**: Create and manage brands with DNA (colors, typography, voice)
    - **Content Creation**: Manage creation projects and campaigns
    - **AI Generation**: Track AI-generated assets (images, videos)
    - **Social Media Posts**: Create and schedule posts with performance metrics
    - **Analytics**: Platform insights and engagement tracking
    - **Template Search**: Find templates using natural language descriptions

    ## Authentication:
    This API supports two authentication methods:

    ### 1. JWT Bearer Token (for Web Users)
    - Obtain JWT token from SIA Solutions OAuth endpoint
    - Include in header: `Authorization: Bearer <token>`

    ### 2. API Key (for Service-to-Service)
    - Use for server-to-server communication
    - Include in header: `X-API-Key: sia_<key>`

    ## Quick Start:
    1. Generate a test token: POST `/api/auth/test-token/`
    2. Use the token in the "Authorize" dialog
    3. Test endpoints without restrictions

    ## Public Endpoints (No Auth Required):
    - `GET /api/health/` - Health check
    - `GET /api/templates/` - List templates
    - `POST /api/templates/search/` - Search templates
    ''',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SCHEMA_PATH_PREFIX': r'/api/',
    'TAGS': [
        {'name': 'Health', 'description': 'System health and status checks'},
        {'name': 'Templates', 'description': 'Template listing and retrieval operations'},
        {'name': 'Search', 'description': 'Semantic similarity search using vector embeddings'},
        {'name': 'Admin', 'description': 'Administrative operations (requires admin privileges)'},
        {'name': 'Brands', 'description': 'Brand management and identity'},
        {'name': 'Brand DNA', 'description': 'Brand DNA extraction and management'},
        {'name': 'Creations', 'description': 'Content creation projects and campaigns'},
        {'name': 'Generations', 'description': 'AI-generated visual assets'},
        {'name': 'Posts', 'description': 'Social media posts and performance metrics'},
        {'name': 'Platform Insights', 'description': 'Time-series analytics for brand growth'},
        {'name': 'Media Files', 'description': 'Digital asset management'},
    ],
    'EXAMPLES_COMPONENT_SPLIT_REQUEST': True,
    'SORT_OPERATION_PARAMETERS': True,

    # Security schemes for Swagger UI
    'SECURITY': [
        {'SIA JWT Auth': []},
        {'SIA API Key': []},
    ],

    # Component security schemes
    'APPEND_COMPONENTS': {
        'securitySchemes': {
            'SIA JWT Auth': {
                'type': 'http',
                'scheme': 'bearer',
                'bearerFormat': 'JWT',
                'description': 'SIA Solutions JWT token. Obtain from /api/auth/test-token/ or SIA login.'
            },
            'SIA API Key': {
                'type': 'apiKey',
                'in': 'header',
                'name': 'X-API-Key',
                'description': 'SIA Solutions API key for service authentication. Format: sia_<32-char>_<16-char>'
            }
        }
    },
}


# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': LOG_LEVEL,
    },
}
