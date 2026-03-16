import uuid
from django.db import models

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
        ('image', 'Image'),
        ('copy', 'Copy'),
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
        'brand_dna_extractor.Brand',
        on_delete=models.CASCADE,
        related_name='posts',
        db_column='brand_uuid'
    )

    preview = models.ForeignKey(
        'creation_studio.Preview',
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
    platforms = models.CharField(max_length=255, blank=True, help_text="Comma-separated platforms")

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
        'brand_dna_extractor.Brand',
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