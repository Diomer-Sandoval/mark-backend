"""
Models for the Template Vector Database and Core Creation Studio.

This module provides models for:
1. Template Vector Database - storing marketing templates with embeddings
2. Core Creation Studio - Brands, Creations, Generations, Posts, etc.

Supports both SQLite (development) and PostgreSQL with pgvector (production).
"""

import json
import numpy as np
from django.db import models, connection
from django.conf import settings

# Import core models
from .models_core import (
    Brand,
    BrandDNA,
    Creation,
    Generation,
    Post,
    PlatformInsight,
    MediaFile,
    generate_uuid,
)


class TemplateDocument(models.Model):
    """
    Stores marketing templates with embeddings for semantic search.
    
    Fields:
        - content: Combined text for embedding (ai_description + use_cases + keywords + etc.)
        - metadata: Full template data as JSON (original enriched template record)
        - embedding: Vector embedding for similarity search (stored differently based on DB)
        - created_at: Timestamp when the record was created
        - updated_at: Timestamp when the record was last updated
    """
    
    # The combined text that was embedded
    content = models.TextField(
        help_text="Combined embedding text: ai_description + use_cases + keywords + industry + mood + colors"
    )
    
    # Full template metadata as JSON
    metadata = models.JSONField(
        default=dict,
        help_text="Full original template record from enriched_templates.json"
    )
    
    # For SQLite: store embedding as JSON string
    # For PostgreSQL: we'll use pgvector (handled via RawSQL or separate migration)
    embedding_json = models.JSONField(
        null=True, blank=True,
        help_text="Embedding vector stored as JSON array (for SQLite compatibility)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'template_documents'
        indexes = [
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        template_id = self.metadata.get('id', 'unknown')
        title = self.metadata.get('title', 'Untitled')
        return f"Template {template_id}: {title[:50]}"
    
    def get_embedding_as_numpy(self):
        """Convert embedding to numpy array for similarity calculations."""
        if self.embedding_json:
            return np.array(self.embedding_json, dtype=np.float32)
        return None
    
    def set_embedding_from_numpy(self, embedding_array):
        """Store numpy array as JSON."""
        self.embedding_json = embedding_array.tolist()


class TemplateSearchService:
    """
    Service class for semantic similarity search on templates.
    
    Provides methods to:
        - Find similar templates using cosine similarity
        - Match documents with query embeddings
        - Validate the database state
    
    Usage:
        service = TemplateSearchService()
        results = service.match_documents(query_embedding, match_count=50)
    """
    
    def __init__(self):
        self.using_postgres = self._check_postgres()
    
    def _check_postgres(self):
        """Check if we're using PostgreSQL database."""
        return 'postgresql' in connection.settings_dict['ENGINE']
    
    def cosine_similarity(self, vec1, vec2):
        """
        Calculate cosine similarity between two vectors.
        
        Args:
            vec1: First vector (numpy array or list)
            vec2: Second vector (numpy array or list)
        
        Returns:
            float: Cosine similarity score (0 to 1)
        """
        vec1 = np.array(vec1, dtype=np.float32)
        vec2 = np.array(vec2, dtype=np.float32)
        
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(np.dot(vec1, vec2) / (norm1 * norm2))
    
    def match_documents(self, query_embedding, match_count=50):
        """
        Find the most similar templates to a query embedding.
        
        Args:
            query_embedding: Vector to search against (list or numpy array)
            match_count: Number of results to return (default: 50)
        
        Returns:
            List of tuples: (template_document, similarity_score)
        """
        query_embedding = np.array(query_embedding, dtype=np.float32)
        
        # Get all documents with embeddings
        documents = TemplateDocument.objects.exclude(embedding_json__isnull=True)
        
        # Calculate similarity for each
        scored_docs = []
        for doc in documents:
            doc_embedding = doc.get_embedding_as_numpy()
            if doc_embedding is not None:
                similarity = self.cosine_similarity(query_embedding, doc_embedding)
                scored_docs.append((doc, similarity))
        
        # Sort by similarity (highest first) and return top K
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        return scored_docs[:match_count]
    
    def get_template_image_url(self, template_doc):
        """
        Extract the preview image URL from template metadata.
        
        Args:
            template_doc: TemplateDocument instance
        
        Returns:
            str: Image URL or None
        """
        metadata = template_doc.metadata
        
        # Try different possible fields for image URL
        if metadata.get('preview_image_url'):
            return metadata['preview_image_url']
        if metadata.get('preview_image_path'):
            return metadata['preview_image_path']
        
        return None
    
    def validate_database(self):
        """
        Run validation checks on the database.
        
        Returns:
            dict: Validation results with counts and status
        """
        total = TemplateDocument.objects.count()
        with_embeddings = TemplateDocument.objects.exclude(embedding_json__isnull=True).count()
        empty_content = TemplateDocument.objects.filter(content__isnull=True).count() + \
                       TemplateDocument.objects.filter(content='').count()
        
        return {
            'total_templates': total,
            'with_embeddings': with_embeddings,
            'empty_content': empty_content,
            'is_valid': total > 0 and with_embeddings == total and empty_content == 0
        }


# SQL Functions for PostgreSQL (to be run in migration or manually)
"""
When migrating to PostgreSQL with pgvector, run these SQL commands:

1. Enable pgvector extension:
   CREATE EXTENSION IF NOT EXISTS vector;

2. Add vector column (alternative to JSON storage):
   ALTER TABLE template_documents ADD COLUMN embedding vector(1536);

3. Create similarity search function:
   CREATE OR REPLACE FUNCTION match_documents(
       query_embedding VECTOR(1536),
       match_count INT DEFAULT 50
   ) RETURNS TABLE (
       id BIGINT,
       content TEXT,
       metadata JSONB,
       similarity FLOAT
   ) LANGUAGE plpgsql AS $$
   BEGIN
       RETURN QUERY
       SELECT
           d.id, d.content, d.metadata,
           1 - (d.embedding <=> query_embedding) AS similarity
       FROM template_documents d
       ORDER BY d.embedding <=> query_embedding
       LIMIT match_count;
   END; $$;

4. Create IVFFlat index for fast similarity search:
   CREATE INDEX ON template_documents
       USING ivfflat (embedding vector_cosine_ops)
       WITH (lists = 100);
"""
