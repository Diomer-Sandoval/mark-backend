"""
Core Models for the Creation Studio App.

This module provides models for managing:
- Brands and Brand DNA
- Content Creations and Generations
- Posts and Platform Insights
- Media Files
"""

import uuid
from django.db import models
from django.core.validators import URLValidator


def generate_uuid():
    """Generate a standard UUID4."""
    return uuid.uuid4()


class Brand(models.Model):
    """
    Central identity hub for each client.
    
    Acts as the master record from which all strategies, 
    content creations, and performance analytics descend.
    """
    
    # Primary key using standard UUID4 format
    uuid = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4,
        editable=False
    )
    
    # Foreign keys
    dna = models.OneToOneField(
        'BrandDNA',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='brand',
        db_column='dna_id'
    )
    
    # SIA Solutions integration - User and Tenant tracking
    user_id = models.CharField(
        max_length=36,
        null=True,
        blank=True,
        db_index=True,
        help_text="SIA User UUID (from OAuth/JWT) - who owns this brand"
    )
    
    tenant_id = models.CharField(
        max_length=36,
        null=True,
        blank=True,
        db_index=True,
        help_text="SIA Tenant UUID - which organization this brand belongs to"
    )
    
    # Brand information
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    page_url = models.URLField(max_length=500, blank=True, validators=[URLValidator()])
    logo_url = models.URLField(max_length=500, blank=True, validators=[URLValidator()])
    
    # Status and metadata
    is_active = models.BooleanField(default=True)
    industry = models.CharField(max_length=100, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'brands'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['is_active']),
            models.Index(fields=['industry']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.uuid})"


class BrandDNA(models.Model):
    """
    Algorithmic DNA repository of the brand.
    
    Stores technical and creative constraints (colors, typography, voice)
    that feed the Strategist and Prompt Engineer nodes.
    """
    
    uuid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    # Color palette (hex values)
    primary_color = models.CharField(max_length=7, blank=True, help_text="Hex color code")
    secondary_color = models.CharField(max_length=7, blank=True, help_text="Hex color code")
    accent_color = models.CharField(max_length=7, blank=True, help_text="Hex color code")
    complementary_color = models.CharField(max_length=7, blank=True, help_text="Hex color code")
    
    # Typography
    font_body_family = models.CharField(max_length=100, blank=True)
    font_headings_family = models.CharField(max_length=100, blank=True)
    
    # Brand voice
    voice_tone = models.CharField(max_length=255, blank=True)
    keywords = models.TextField(blank=True, help_text="Comma-separated brand keywords")
    description = models.TextField(blank=True, help_text="Brand description and positioning")
    
    # Raw extraction data (for reference)
    raw_data = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'brand_dna'
        verbose_name = 'Brand DNA'
        verbose_name_plural = 'Brand DNA'
    
    def __str__(self):
        return f"BrandDNA {self.uuid}"


class Creation(models.Model):
    """
    Orchestrator of the content lifecycle.
    
    Manages the state of each generation request from webhook entry
    to completion. Records user intent, emotional impact, and target platforms.
    """
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    POST_TYPE_CHOICES = [
        ('post', 'Post'),
        ('carousel', 'Carousel'),
        ('reel', 'Reel'),
        ('story', 'Story'),
        ('infographic', 'Infographic'),
    ]
    
    uuid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    brand = models.ForeignKey(
        Brand,
        on_delete=models.CASCADE,
        related_name='creations',
        db_column='brand_uuid'
    )
    
    # SIA Solutions integration - track who created this
    user_id = models.CharField(
        max_length=36,
        null=True,
        blank=True,
        db_index=True,
        help_text="SIA User UUID who created this project"
    )
    
    # Creation details
    title = models.CharField(max_length=500)
    post_type = models.CharField(max_length=20, choices=POST_TYPE_CHOICES, default='post')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    platforms = models.CharField(
        max_length=255, 
        blank=True,
        help_text="Comma-separated platforms (e.g., instagram, tiktok)"
    )
    post_tone = models.CharField(max_length=50, blank=True, help_text="Desired emotional impact")
    
    # Original prompt/intent
    original_prompt = models.TextField(blank=True)
    
    # Research data (stored as JSON)
    research_data = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'creations'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['brand', 'status']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.uuid})"
    
    @property
    def platforms_list(self):
        """Return platforms as a list."""
        return [p.strip() for p in self.platforms.split(',') if p.strip()]


class Generation(models.Model):
    """
    Detailed ledger of AI iterations.
    
    Logs every individual attempt generated by vision models.
    Self-referencing architecture (parent_uuid) maintains genealogical history
    of how an asset evolved from first draft to final version.
    """
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('done', 'Done'),
        ('failed', 'Failed'),
    ]
    
    MEDIA_TYPE_CHOICES = [
        ('image', 'Image'),
        ('video', 'Video'),
    ]
    
    uuid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    creation = models.ForeignKey(
        Creation,
        on_delete=models.CASCADE,
        related_name='generations',
        db_column='creation_uuid'
    )
    
    # Self-referencing for version history
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='children',
        db_column='parent_uuid'
    )
    
    # Generation details
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPE_CHOICES, default='image')
    prompt = models.TextField(help_text="The optimized super-prompt used")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Generation parameters (for reproducibility)
    generation_params = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'generations'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['creation', 'status']),
            models.Index(fields=['status']),
            models.Index(fields=['parent']),
        ]
    
    def __str__(self):
        return f"Generation {self.uuid}"


class Post(models.Model):
    """
    Final production deliverable and its real-world performance.
    
    Convergence point where strategic copywriting meets final visual asset.
    Acts as a success-tracking engine logging interaction metrics.
    """
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('published', 'Published'),
        ('failed', 'Failed'),
    ]
    
    POST_TYPE_CHOICES = [
        ('post', 'Post'),
        ('carousel', 'Carousel'),
        ('reel', 'Reel'),
        ('story', 'Story'),
        ('infographic', 'Infographic'),
    ]
    
    uuid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    brand = models.ForeignKey(
        Brand,
        on_delete=models.CASCADE,
        related_name='posts',
        db_column='brand_uuid'
    )
    
    # SIA Solutions integration - track who owns this post
    user_id = models.CharField(
        max_length=36,
        null=True,
        blank=True,
        db_index=True,
        help_text="SIA User UUID who owns this post"
    )
    
    creation = models.ForeignKey(
        Creation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='posts',
        db_column='creation_uuid'
    )
    
    # Post content
    copy = models.TextField(blank=True, help_text="Post caption/copy")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Scheduling
    scheduled_date = models.DateTimeField(null=True, blank=True)
    executed_at = models.DateTimeField(null=True, blank=True)
    
    # Post metadata
    post_type = models.CharField(max_length=20, choices=POST_TYPE_CHOICES, default='post')
    platforms = models.CharField(max_length=255, blank=True, help_text="Comma-separated platforms")
    
    # Performance metrics
    likes = models.PositiveIntegerField(default=0)
    comments = models.PositiveIntegerField(default=0)
    shares = models.PositiveIntegerField(default=0)
    reach = models.PositiveIntegerField(default=0)
    engagement_rate = models.FloatField(default=0.0)
    
    # Additional metrics (flexible storage)
    metrics = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'posts'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['brand', 'status']),
            models.Index(fields=['status']),
            models.Index(fields=['scheduled_date']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Post {self.uuid}"
    
    def calculate_engagement_rate(self):
        """Calculate engagement rate based on reach."""
        if self.reach > 0:
            total_engagement = self.likes + self.comments + self.shares
            return (total_engagement / self.reach) * 100
        return 0.0


class PlatformInsight(models.Model):
    """
    Time-series observability for brand growth across social networks.
    
    Unlike POSTS table which tracks individual content performance,
    this monitors macro-growth across each social network.
    """
    
    PLATFORM_CHOICES = [
        ('instagram', 'Instagram'),
        ('facebook', 'Facebook'),
        ('linkedin', 'LinkedIn'),
        ('tiktok', 'TikTok'),
        ('twitter', 'Twitter/X'),
        ('pinterest', 'Pinterest'),
        ('youtube', 'YouTube'),
    ]
    
    uuid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    brand = models.ForeignKey(
        Brand,
        on_delete=models.CASCADE,
        related_name='platform_insights',
        db_column='brand_uuid'
    )
    
    # Platform and date
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    date = models.DateField()
    
    # Metrics
    followers = models.PositiveIntegerField(default=0)
    impressions = models.PositiveIntegerField(default=0)
    reach = models.PositiveIntegerField(default=0)
    engagement_rate = models.FloatField(default=0.0)
    
    # Additional metrics
    metrics = models.JSONField(default=dict, blank=True)
    
    # Timestamp
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'platform_insights'
        ordering = ['-date', '-created_at']
        unique_together = ['brand', 'platform', 'date']
        indexes = [
            models.Index(fields=['brand', 'platform']),
            models.Index(fields=['date']),
            models.Index(fields=['platform']),
        ]
    
    def __str__(self):
        return f"{self.brand.name} - {self.platform} ({self.date})"


class MediaFile(models.Model):
    """
    Logistical warehouse for digital assets.
    
    Manages persistence and availability of binary files by linking
    secure CDN URLs to their corresponding generation.
    """
    
    FILE_TYPE_CHOICES = [
        ('image/jpeg', 'JPEG Image'),
        ('image/png', 'PNG Image'),
        ('image/webp', 'WebP Image'),
        ('video/mp4', 'MP4 Video'),
    ]
    
    uuid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    generation = models.ForeignKey(
        Generation,
        on_delete=models.CASCADE,
        related_name='media_files',
        db_column='generation_uuid'
    )
    
    # File information
    url = models.URLField(max_length=1000, validators=[URLValidator()])
    file_type = models.CharField(max_length=30, choices=FILE_TYPE_CHOICES)
    
    # Storage metadata
    file_size = models.PositiveIntegerField(null=True, blank=True, help_text="Size in bytes")
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    
    # CDN/Storage info
    storage_provider = models.CharField(max_length=50, blank=True, default='cloudinary')
    storage_metadata = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'media_files'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['generation']),
            models.Index(fields=['file_type']),
        ]
    
    def __str__(self):
        return f"Media {self.uuid}"
