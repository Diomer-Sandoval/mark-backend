"""
Management command to populate dummy data for testing.

Usage:
    python manage.py populate_dummy_data
    python manage.py populate_dummy_data --user-id=<uuid> --tenant-id=<uuid>
"""

from django.core.management.base import BaseCommand
from creation_studio.models import (
    Brand, BrandDNA, Creation, Generation,
    Preview, PreviewItem, Post, PlatformInsight
)


class Command(BaseCommand):
    help = 'Populate database with dummy data for testing'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=str,
            default='550e8400-e29b-41d4-a716-446655440000',
            help='SIA User UUID to associate with dummy data'
        )
        parser.add_argument(
            '--tenant-id',
            type=str,
            default='660e8400-e29b-41d4-a716-446655440000',
            help='SIA Tenant UUID to associate with dummy data'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before creating new'
        )
    
    def handle(self, *args, **options):
        user_id = options['user_id']
        tenant_id = options['tenant_id']
        
        if options['clear']:
            self.stdout.write('Clearing existing data...')
            Post.objects.all().delete()
            PreviewItem.objects.all().delete()
            Preview.objects.all().delete()
            Generation.objects.all().delete()
            Creation.objects.all().delete()
            Brand.objects.all().delete()
            BrandDNA.objects.all().delete()
        
        self.stdout.write(f'Creating dummy data for user: {user_id}')
        
        # Create Brand DNA
        dna = BrandDNA.objects.create(
            primary_color='#007AFF',
            secondary_color='#FFFFFF',
            accent_color='#FF9500',
            complementary_color='#34C759',
            font_body_family='SF Pro Text',
            font_headings_family='SF Pro Display',
            voice_tone='Professional, innovative, friendly',
            keywords='technology, innovation, premium, sleek',
            description='A premium technology brand focused on innovation',
            archetype='The Creator',
            target_audience='Tech-savvy professionals and innovators'
        )
        self.stdout.write(f'  Created BrandDNA: {dna.uuid}')
        
        # Create Brand
        brand = Brand.objects.create(
            dna=dna,
            name='TechCorp Industries',
            slug='techcorp-industries',
            page_url='https://techcorp.example.com',
            logo_url='https://techcorp.example.com/logo.png',
            is_active=True,
            industry='Technology',
            user_id=user_id,
            tenant_id=tenant_id
        )
        self.stdout.write(f'  Created Brand: {brand.uuid}')
        
        # Create Creations
        creation1 = Creation.objects.create(
            brand=brand,
            title='Summer Product Launch 2026',
            post_type='carousel',
            status='done',
            platforms='instagram,linkedin,tiktok',
            post_tone='exciting, promotional'
        )
        self.stdout.write(f'  Created Creation: {creation1.uuid}')
        
        creation2 = Creation.objects.create(
            brand=brand,
            title='Holiday Campaign Video',
            post_type='reel',
            status='in_progress',
            platforms='instagram,tiktok',
            post_tone='festive, heartwarming'
        )
        self.stdout.write(f'  Created Creation: {creation2.uuid}')
        
        # Create Generations
        gen1 = Generation.objects.create(
            creation=creation1,
            type='image',
            prompt='Modern product showcase with gradient background, minimal style',
            content='https://res.cloudinary.com/example/image/upload/v12345/product1.png',
            status='done'
        )
        self.stdout.write(f'  Created Generation: {gen1.uuid}')
        
        gen2 = Generation.objects.create(
            creation=creation1,
            type='image',
            prompt='Product detail shot, macro photography, studio lighting',
            content='https://res.cloudinary.com/example/image/upload/v12345/product2.png',
            status='done'
        )
        self.stdout.write(f'  Created Generation: {gen2.uuid}')
        
        gen3 = Generation.objects.create(
            creation=creation1,
            type='copy',
            prompt='Write a caption for the summer launch',
            content='Introducing our Summer Collection! 🌞✨ Get ready to elevate your style.',
            status='done'
        )
        self.stdout.write(f'  Created Generation: {gen3.uuid}')

        # Create Preview
        preview = Preview.objects.create(
            version_name='V1 - Global Launch',
            internal_notes='Final selection for the main campaign'
        )
        PreviewItem.objects.create(preview=preview, generation=gen1, position=1)
        PreviewItem.objects.create(preview=preview, generation=gen2, position=2)
        PreviewItem.objects.create(preview=preview, generation=gen3, position=3)
        self.stdout.write(f'  Created Preview: {preview.uuid} with 3 items')
        
        # Create Posts
        post1 = Post.objects.create(
            brand=brand,
            user_id=user_id,
            preview=preview,
            final_copy='Introducing our Summer Collection! 🌞✨\n\n#SummerVibes #NewCollection #TechCorp',
            status='published',
            executed_at='2026-03-05T14:30:00Z',
            post_type='carousel',
            platforms='instagram,linkedin',
            likes=1250,
            comments=45,
            shares=12,
            reach=15600,
            engagement_rate=8.45
        )
        self.stdout.write(f'  Created Post: {post1.uuid}')
        
        # Create Platform Insights
        from datetime import date, timedelta
        
        for i in range(30):
            insight_date = date(2026, 2, 1) + timedelta(days=i)
            PlatformInsight.objects.create(
                brand=brand,
                platform='instagram',
                date=insight_date,
                followers=10000 + (i * 50),
                impressions=50000 + (i * 1000),
                reach=35000 + (i * 500),
                engagement_rate=5.5 + (i * 0.1)
            )
        self.stdout.write(f'  Created 30 PlatformInsight records for Instagram')
        
        self.stdout.write(self.style.SUCCESS('\n[SUCCESS] Dummy data created successfully!'))
