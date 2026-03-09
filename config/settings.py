from pathlib import Path
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-n81qjcd3%9t^v3k7v4+nc#njowj%jz*xx&%n+@d!=)n!*&yr#t'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    'corsheaders',
    'creation_studio',
    'brand_dna_extractor',
    'rest_framework',
    'drf_spectacular',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

MIDDLEWARE = [
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


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

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


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = 'static/'

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
        'creation_studio.auth.SIAJWTAuthentication',
        'creation_studio.auth.SIAAPIKeyAuthentication',
    ],
}

# Development mode - set to True to allow testing without authentication
# In production, this should always be False
DEV_MODE_ALLOW_UNAUTHENTICATED = os.getenv('DEV_MODE_ALLOW_UNAUTHENTICATED', 'False').lower() == 'true'

if DEV_MODE_ALLOW_UNAUTHENTICATED:
    REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES'] = ['rest_framework.permissions.AllowAny']
    REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'] = []

# drf-spectacular Configuration (Swagger/OpenAPI)
# SIA Solutions Integration Settings
SIA_BASE_URL = os.getenv('SIA_BASE_URL', 'https://sia-backend-sbw7.onrender.com')  # Production SIA backend
SIA_JWT_SECRET = os.getenv('SIA_JWT_SECRET', None)  # For local JWT validation (optional)

SPECTACULAR_SETTINGS = {
    # Custom authentication extensions
    'AUTHENTICATION_EXTENSIONS': [
        'creation_studio.auth.SIAJWTAuthenticationExtension',
        'creation_studio.auth.SIAAPIKeyAuthenticationExtension',
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
