"""
Core Models for the Creation Studio App.

This module provides models for managing:
- Brands and Brand DNA
- Content Creations and Generations
- Posts and Platform Insights
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

    # Brand information
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    page_url = models.URLField(max_length=500, blank=True, validators=[URLValidator()])
    primary_color = models.CharField(max_length=7, blank=True, help_text="Hex color code")
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

    # Brand strategy
    archetype = models.CharField(max_length=100, blank=True, help_text="Brand archetype")
    target_audience = models.CharField(max_length=255, blank=True, help_text="Target audience description")

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
        ('video', 'Video'),
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
        db_column='brand_uuid',
        null=True,
        blank=True,
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

    TYPE_CHOICES = [
        ('image', 'Image'),
        ('video', 'Video'),
        ('copy', 'Copy'),
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
    type = models.CharField(max_length=50, choices=TYPE_CHOICES, default='image')
    prompt = models.TextField(blank=True, help_text="The optimized super-prompt used")
    content = models.TextField(blank=True, help_text="Generated content output")
    keywords = models.CharField(max_length=500, blank=True, help_text="Comma-separated keywords")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

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


class Preview(models.Model):
    """
    A versioned preview composition of generations.

    Groups selected generations into a named preview version
    that can be reviewed before finalizing as a post.
    """

    uuid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Preview details
    version_name = models.CharField(max_length=255, blank=True)
    internal_notes = models.TextField(blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'preview'
        ordering = ['-created_at']

    def __str__(self):
        return f"Preview {self.version_name or self.uuid}"


class PreviewItem(models.Model):
    """
    Junction table linking Previews to Generations.

    Each item represents a specific generation used in a preview,
    with a position for ordering.
    """

    uuid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    preview = models.ForeignKey(
        Preview,
        on_delete=models.CASCADE,
        related_name='items',
        db_column='preview_uuid'
    )

    generation = models.ForeignKey(
        Generation,
        on_delete=models.CASCADE,
        related_name='preview_items',
        db_column='generation_uuid'
    )

    position = models.IntegerField(default=0)

    class Meta:
        db_table = 'preview_items'
        ordering = ['position']
        indexes = [
            models.Index(fields=['preview', 'position']),
        ]

    def __str__(self):
        return f"PreviewItem {self.uuid} (pos={self.position})"


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
        ('video', 'Video'),
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

    preview = models.ForeignKey(
        Preview,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='posts',
        db_column='preview_uuid'
    )

    # Post content
    final_copy = models.TextField(blank=True, help_text="Final post caption/copy")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')

    # Scheduling
    scheduled_date = models.DateTimeField(null=True, blank=True)
    executed_at = models.DateTimeField(null=True, blank=True)

    # Post metadata
    post_type = models.CharField(max_length=20, choices=POST_TYPE_CHOICES, default='post')

    # Performance metrics
    likes = models.PositiveIntegerField(default=0)
    comments = models.PositiveIntegerField(default=0)
    shares = models.PositiveIntegerField(default=0)
    reach = models.PositiveIntegerField(default=0)
    engagement_rate = models.FloatField(default=0.0)

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
    Store URLs and metadata for files associated with a Generation.

    Allows a single generation to have multiple assets (e.g. video + thumbnail),
    or simply stores the primary visual output in a structured way.
    """

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

    # File details
    url = models.URLField(max_length=1000, help_text="Public URL of the asset (e.g. Cloudinary)")
    file_type = models.CharField(max_length=100, blank=True, help_text="MIME type (e.g. image/jpeg, video/mp4)")
    
    # Metadata for the file
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    file_size = models.PositiveIntegerField(null=True, blank=True, help_text="Size in bytes")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'media_files'
        ordering = ['created_at']
        verbose_name = 'Media File'
        verbose_name_plural = 'Media Files'

    def __str__(self):
        return f"MediaFile {self.uuid} ({self.file_type})"
