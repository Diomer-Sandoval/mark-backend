"""
Django management command to ingest templates into vector database.

Usage:
    python manage.py ingest_templates
    python manage.py ingest_templates --test-search
    python manage.py ingest_templates --no-clear
"""

from django.core.management.base import BaseCommand
from creation_studio.templates.ingest import ingest_templates, validate_ingestion, test_similarity_search


class Command(BaseCommand):
    help = 'Ingest marketing templates from enriched_templates.json into vector database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--json-path',
            help='Path to enriched_templates.json (default: templates/enriched_templates.json)'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Number of templates to embed per API call (default: 100)'
        )
        parser.add_argument(
            '--skip-validation',
            action='store_true',
            help='Skip validation after ingestion'
        )
        parser.add_argument(
            '--test-search',
            action='store_true',
            help='Run similarity search test after ingestion'
        )
        parser.add_argument(
            '--no-clear',
            action='store_true',
            help='Do not clear existing data before ingestion'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.HTTP_INFO('Starting template ingestion...'))
        
        # Run ingestion
        ingest_templates(
            json_path=options['json_path'],
            batch_size=options['batch_size'],
            clear_existing=not options['no_clear']
        )
        
        # Run validation unless skipped
        if not options['skip_validation']:
            validate_ingestion()
        
        # Test search if requested
        if options['test_search']:
            test_similarity_search()
        
        self.stdout.write(self.style.SUCCESS('\n✅ Done!'))
