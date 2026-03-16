import numpy as np
from django.db import connection
from ..models import TemplateDocument

class TemplateSearchService:
    """
    Service class for semantic similarity search on templates.

    Provides methods to:
        - Find similar templates using cosine similarity
        - Match documents with query embeddings
        - Validate the database state
    """

    def __init__(self):
        self.using_postgres = self._check_postgres()

    def _check_postgres(self):
        """Check if we're using PostgreSQL database."""
        return 'postgresql' in connection.settings_dict['ENGINE']

    def cosine_similarity(self, vec1, vec2):
        """
        Calculate cosine similarity between two vectors.
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
