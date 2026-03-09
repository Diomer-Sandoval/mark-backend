"""
Template Ingestion Script for Vector Database.

This script:
    1. Loads enriched_templates.json
    2. Filters for processed templates (with AI metadata)
    3. Builds embedding text for each template
    4. Generates embeddings using OpenAI API
    5. Stores templates and embeddings in the database

Usage:
    # Option 1: Set environment variable
    export OPENAI_API_KEY="sk-..."
    
    # Run the script
    python creation_studio/ingest_templates.py
    
    # Or via Django management
    python manage.py ingest_templates

Environment Variables:
    OPENAI_API_KEY: Required. Your OpenAI API key.
    BATCH_SIZE: Optional. Number of templates to embed per API call (default: 100)
    JSON_PATH: Optional. Path to enriched_templates.json (default: templates/enriched_templates.json)
"""

import os
import sys
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

import logging
from typing import List, Dict, Any
from creation_studio.embedding_service import TemplateEmbeddingService
from creation_studio.models import TemplateDocument

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
    service = TemplateEmbeddingService(api_key="dummy")  # Just for the method
    
    processed = []
    skipped_reasons = {
        'no_ai_description': 0,
        'processing_error': 0,
        'no_use_cases': 0
    }
    
    for template in templates:
        # Check AI description
        if not template.get('ai_description'):
            skipped_reasons['no_ai_description'] += 1
            continue
        
        # Check for processing errors
        if template.get('processing_error'):
            skipped_reasons['processing_error'] += 1
            continue
        
        # Check use cases
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
    # Set default path
    if json_path is None:
        json_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'templates', 'enriched_templates.json'
        )
    
    # Check for API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        logger.error("OPENAI_API_KEY environment variable not set!")
        logger.error("Please set your OpenAI API key:")
        logger.error("  export OPENAI_API_KEY='sk-...'")
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
        if text:  # Only include if we have content
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
            doc = TemplateDocument.objects.create(
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
    
    from creation_studio.models import TemplateSearchService
    
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
    
    from creation_studio.models import TemplateSearchService
    
    # Initialize service
    service = TemplateSearchService()
    
    # Check if we have data
    if TemplateDocument.objects.count() == 0:
        logger.error("No templates in database! Run ingestion first.")
        return
    
    # Create a test query embedding
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        logger.error("OPENAI_API_KEY not set, skipping test")
        return
    
    embedding_service = TemplateEmbeddingService(api_key=api_key)
    
    # Test query
    test_query = "bold tech product launch announcement with dark background"
    logger.info(f"Test query: '{test_query}'")
    
    query_embedding = embedding_service.embed_text(test_query)
    
    # Search
    results = service.match_documents(query_embedding, match_count=5)
    
    logger.info("\nTop 5 matching templates:")
    for i, (doc, similarity) in enumerate(results, 1):
        template_id = doc.metadata.get('id', 'unknown')
        title = doc.metadata.get('title', 'Untitled')[:40]
        style = doc.metadata.get('design_style', 'unknown')
        logger.info(f"  {i}. ID: {template_id} | {title}... | Style: {style} | Similarity: {similarity:.4f}")
    
    logger.info("\n✅ Similarity search test complete!")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Ingest templates into vector database')
    parser.add_argument('--json-path', help='Path to enriched_templates.json')
    parser.add_argument('--batch-size', type=int, default=100, help='Batch size for embeddings')
    parser.add_argument('--skip-validation', action='store_true', help='Skip validation after ingestion')
    parser.add_argument('--test-search', action='store_true', help='Run similarity search test after ingestion')
    parser.add_argument('--clear', action='store_true', default=True, help='Clear existing data before ingestion')
    parser.add_argument('--no-clear', dest='clear', action='store_false', help='Do not clear existing data')
    
    args = parser.parse_args()
    
    # Run ingestion
    ingest_templates(
        json_path=args.json_path,
        batch_size=args.batch_size,
        clear_existing=args.clear
    )
    
    # Run validation unless skipped
    if not args.skip_validation:
        validate_ingestion()
    
    # Test search if requested
    if args.test_search:
        test_similarity_search()
