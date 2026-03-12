"""
OpenAI Embedding Service for Template Vector Database.

This module handles:
    - Building embedding text from template metadata
    - Generating embeddings via OpenAI API
    - Batch processing for efficiency
"""

import os
import time
import logging
from typing import List, Dict, Any, Optional
from openai import OpenAI

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TemplateEmbeddingService:
    """
    Service for generating embeddings of marketing templates using OpenAI API.

    Uses text-embedding-3-small model by default (1536 dimensions).
    Supports batch processing for efficient API usage.

    Usage:
        service = TemplateEmbeddingService(api_key="your-api-key")
        embedding = service.embed_text("Your text here")
        embeddings = service.embed_batch(["text1", "text2", "text3"])
    """

    # Recommended model: text-embedding-3-small
    # Dimensions: 1536
    # Cost-effective and high quality
    DEFAULT_MODEL = "text-embedding-3-small"
    DEFAULT_DIMENSIONS = 1536

    # OpenAI recommends batch sizes up to 2048, but we'll use smaller for reliability
    DEFAULT_BATCH_SIZE = 100

    def __init__(self, api_key: Optional[str] = None, model: str = None):
        """
        Initialize the embedding service.

        Args:
            api_key: OpenAI API key. If not provided, reads from OPENAI_API_KEY env var.
            model: Embedding model to use. Defaults to text-embedding-3-small.
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError(
                "OpenAI API key required. Provide it as argument or set OPENAI_API_KEY environment variable."
            )

        self.client = OpenAI(api_key=self.api_key)
        self.model = model or self.DEFAULT_MODEL

        logger.info(f"EmbeddingService initialized with model: {self.model}")

    def build_embedding_text(self, template: Dict[str, Any]) -> str:
        """
        Build a single text string from template metadata for embedding.

        Combines the most descriptive fields into one searchable text.

        Args:
            template: Template dictionary from enriched_templates.json

        Returns:
            str: Combined text ready for embedding
        """
        parts = []

        # AI-generated description (most important)
        if template.get('ai_description'):
            parts.append(template['ai_description'])

        # Use cases
        if template.get('use_cases'):
            use_cases = ', '.join(template['use_cases'])
            parts.append(f"Use cases: {use_cases}")

        # Keywords
        if template.get('keywords'):
            keywords = ', '.join(template['keywords'])
            parts.append(f"Keywords: {keywords}")

        # Industry fit
        if template.get('industry_fit'):
            industries = ', '.join(template['industry_fit'])
            parts.append(f"Industry: {industries}")

        # Mood/atmosphere
        if template.get('mood'):
            if isinstance(template['mood'], list):
                mood = ', '.join(template['mood'])
            else:
                mood = template['mood']
            parts.append(f"Mood: {mood}")

        # Color palette
        if template.get('color_palette'):
            colors = ', '.join(template['color_palette'])
            parts.append(f"Colors: {colors}")

        # Design style
        if template.get('design_style'):
            parts.append(f"Style: {template['design_style']}")

        # Content elements
        if template.get('content_elements'):
            elements = ', '.join(template['content_elements'])
            parts.append(f"Elements: {elements}")

        # Template type info
        if template.get('template_type'):
            parts.append(f"Type: {template['template_type']}")

        if template.get('sub_type'):
            parts.append(f"Format: {template['sub_type']}")

        # Join all parts with separator
        return ' | '.join(parts)

    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            List of floats: The embedding vector
        """
        # Truncate if too long (OpenAI has token limits)
        # text-embedding-3-small has 8191 token limit
        # Approximate: 1 token ~ 4 characters for English
        max_chars = 32000  # Safe limit
        if len(text) > max_chars:
            text = text[:max_chars]

        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error embedding text: {e}")
            raise

    def embed_batch(self, texts: List[str], batch_size: int = None) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batches.

        Args:
            texts: List of texts to embed
            batch_size: Number of texts per API call (default: 100)

        Returns:
            List of embedding vectors
        """
        batch_size = batch_size or self.DEFAULT_BATCH_SIZE
        all_embeddings = []

        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]

            # Truncate texts if needed
            truncated_batch = []
            max_chars = 32000
            for text in batch:
                if len(text) > max_chars:
                    text = text[:max_chars]
                truncated_batch.append(text)

            try:
                logger.info(f"Embedding batch {i//batch_size + 1}/{(len(texts) + batch_size - 1)//batch_size} "
                          f"({len(batch)} texts)")

                response = self.client.embeddings.create(
                    model=self.model,
                    input=truncated_batch
                )

                # Extract embeddings in order
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)

                # Small delay to respect rate limits
                time.sleep(0.1)

            except Exception as e:
                logger.error(f"Error embedding batch: {e}")
                raise

        return all_embeddings

    def is_processed_template(self, template: Dict[str, Any]) -> bool:
        """
        Check if a template has been properly processed with AI metadata.

        Args:
            template: Template dictionary

        Returns:
            bool: True if template has ai_description and is ready for embedding
        """
        # Must have AI description
        if not template.get('ai_description'):
            return False

        # Must not have processing errors
        if template.get('processing_error'):
            return False

        # Should have some use cases
        if not template.get('use_cases'):
            return False

        return True
