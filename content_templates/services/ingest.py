"""
Template Ingestion for Vector Database.

Provides functions to:
    1. Load enriched_templates.json
    2. Filter for processed templates (with AI metadata)
    3. Build embedding text for each template
    4. Generate embeddings using OpenAI API
    5. Store templates and embeddings in the database

Usage (via management command):
    python manage.py ingest_templates
"""

import os
import sys
import json
import logging
from typing import List, Dict, Any

from .embedding import TemplateEmbeddingService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_templates(json_path: str) -> List[Dict[str, Any]]:
    """
    Load templates from the enriched JSON file.

    Args:
        json_path: Path to enriched_templates.json

    Returns:
        List of template dictionaries
    """
    logger.info(f"Loading templates from: {json_path}")

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    templates = data.get('templates', [])
    metadata = data.get('metadata', {})

    logger.info(f"Total templates in file: {metadata.get('total_templates', len(templates))}")
    logger.info(f"Processed templates: {metadata.get('processed', 'unknown')}")
    logger.info(f"Errors: {metadata.get('errors', 'unknown')}")

    return templates


def filter_processed_templates(templates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filter templates to only include those with AI-generated metadata.

    Args:
        templates: List of all templates

    Returns:
        List of processed templates ready for embedding
    """
    processed = []
    skipped_reasons = {
        'no_ai_description': 0,
        'processing_error': 0,
        'no_use_cases': 0
    }

    for template in templates:
        if not template.get('ai_description'):
            skipped_reasons['no_ai_description'] += 1
            continue

        if template.get('processing_error'):
            skipped_reasons['processing_error'] += 1
            continue

        if not template.get('use_cases'):
            skipped_reasons['no_use_cases'] += 1
            continue

        processed.append(template)

    logger.info(f"Templates to process: {len(processed)}")
    logger.info(f"Skipped: {len(templates) - len(processed)}")
    for reason, count in skipped_reasons.items():
        if count > 0:
            logger.info(f"  - {reason}: {count}")

    return processed


def ingest_templates(
    json_path: str = None,
    batch_size: int = 100,
    clear_existing: bool = True
):
    """
    Main ingestion function.

    Args:
        json_path: Path to enriched_templates.json. Defaults to templates/enriched_templates.json
        batch_size: Number of templates to embed per API call
        clear_existing: If True, clears existing data before ingestion
    """
    from ..models import TemplateDocument

    # Set default path
    if json_path is None:
        json_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'templates', 'enriched_templates.json'
        )

    # Check for API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        logger.error("OPENAI_API_KEY environment variable not set!")
        sys.exit(1)

    # Clear existing data if requested
    if clear_existing:
        count = TemplateDocument.objects.count()
        if count > 0:
            logger.info(f"Clearing {count} existing template documents...")
            TemplateDocument.objects.all().delete()

    # Load templates
    templates = load_templates(json_path)

    # Filter for processed templates
    processed_templates = filter_processed_templates(templates)

    if not processed_templates:
        logger.error("No processed templates found!")
        sys.exit(1)

    # Initialize embedding service
    logger.info("Initializing embedding service...")
    embedding_service = TemplateEmbeddingService(api_key=api_key)

    # Build embedding texts
    logger.info("Building embedding texts...")
    embedding_texts = []
    valid_templates = []

    for template in processed_templates:
        text = embedding_service.build_embedding_text(template)
        if text:
            embedding_texts.append(text)
            valid_templates.append(template)

    logger.info(f"Ready to embed {len(embedding_texts)} templates")

    # Generate embeddings in batches
    logger.info(f"Generating embeddings (batch size: {batch_size})...")
    try:
        embeddings = embedding_service.embed_batch(embedding_texts, batch_size=batch_size)
    except Exception as e:
        logger.error(f"Failed to generate embeddings: {e}")
        sys.exit(1)

    # Store in database
    logger.info("Storing templates in database...")
    created_count = 0

    for i, (template, embedding) in enumerate(zip(valid_templates, embeddings)):
        try:
            TemplateDocument.objects.create(
                content=embedding_texts[i],
                metadata=template,
                embedding_json=embedding
            )
            created_count += 1

            if (i + 1) % 50 == 0:
                logger.info(f"  Stored {i + 1}/{len(valid_templates)} templates...")

        except Exception as e:
            logger.error(f"Error storing template {template.get('id', i)}: {e}")

    logger.info(f"\n✅ Ingestion complete!")
    logger.info(f"Templates stored: {created_count}")
    logger.info(f"Total in database: {TemplateDocument.objects.count()}")


def validate_ingestion():
    """
    Run validation checks on the ingested data.

    Returns True if all checks pass, False otherwise.
    """
    logger.info("\n🔍 Running validation checks...")

    from .search import TemplateSearchService

    service = TemplateSearchService()
    results = service.validate_database()

    logger.info(f"Total templates: {results['total_templates']}")
    logger.info(f"With embeddings: {results['with_embeddings']}")
    logger.info(f"Empty content: {results['empty_content']}")

    if results['is_valid']:
        logger.info("✅ All validation checks passed!")
        return True
    else:
        logger.warning("⚠️ Some validation checks failed")
        return False


def test_similarity_search():
    """
    Run a quick test of the similarity search functionality.
    """
    logger.info("\n🧪 Testing similarity search...")

    from ..models import TemplateDocument
    from .search import TemplateSearchService

    service = TemplateSearchService()

    if TemplateDocument.objects.count() == 0:
        logger.error("No templates in database! Run ingestion first.")
        return

    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        logger.error("OPENAI_API_KEY not set, skipping test")
        return

    embedding_service = TemplateEmbeddingService(api_key=api_key)

    test_query = "bold tech product launch announcement with dark background"
    logger.info(f"Test query: '{test_query}'")

    query_embedding = embedding_service.embed_text(test_query)
    results = service.match_documents(query_embedding, match_count=5)

    logger.info("\nTop 5 matching templates:")
    for i, (doc, similarity) in enumerate(results, 1):
        template_id = doc.metadata.get('id', 'unknown')
        title = doc.metadata.get('title', 'Untitled')[:40]
        style = doc.metadata.get('design_style', 'unknown')
        logger.info(f"  {i}. ID: {template_id} | {title}... | Style: {style} | Similarity: {similarity:.4f}")

    logger.info("\n✅ Similarity search test complete!")
