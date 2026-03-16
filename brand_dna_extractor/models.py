import uuid
from django.db import models
from django.core.validators import URLValidator

def generate_uuid():
    """Generate a standard UUID4."""
    return uuid.uuid4()

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
