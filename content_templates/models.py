"""
Models for the Template Vector Database.

This module provides models for:
1. Template Vector Database - storing marketing templates with embeddings

Supports both SQLite (development) and PostgreSQL with pgvector (production).
"""

import json
import numpy as np
from django.db import models, connection


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
