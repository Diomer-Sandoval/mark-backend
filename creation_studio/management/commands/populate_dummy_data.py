"""
Management command to populate dummy data for testing.

Usage:
    python manage.py populate_dummy_data
    python manage.py populate_dummy_data --user-id=<uuid> --tenant-id=<uuid>
"""

from django.core.management.base import BaseCommand, CommandError
from creation_studio.models_core import (
    Brand, BrandDNA, Creation, Generation,
    Post, PlatformInsight, MediaFile
)


class Command(BaseCommand):
    help = 'Populate database with dummy data for testing'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=str,
            default='550e8400-e29b-41d4-a716-446655440000',
            help='User UUID to associate with dummy data'
        )
        parser.add_argument(
            '--tenant-id',
            type=str,
            default='660e8400-e29b-41d4-a716-446655440000',
            help='Tenant UUID to associate with dummy data'
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
            MediaFile.objects.all().delete()
            Post.objects.all().delete()
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
            raw_data={
                'extracted_from': 'website',
                'confidence': 0.95
            }
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
        
        # Create Brand without DNA
        brand2 = Brand.objects.create(
            name='Fashion Forward',
            slug='fashion-forward',
            page_url='https://fashion.example.com',
            logo_url='https://fashion.example.com/logo.png',
            is_active=True,
            industry='Fashion',
            user_id=user_id,
            tenant_id=tenant_id
        )
        self.stdout.write(f'  Created Brand: {brand2.uuid}')
        
        # Create Creations
        creation1 = Creation.objects.create(
            brand=brand,
            title='Summer Product Launch 2026',
            post_type='carousel',
            status='done',
            platforms='instagram,linkedin,tiktok',
            post_tone='exciting, promotional',
            original_prompt='Create a vibrant carousel showcasing our new summer product line',
            research_data={
                'trends': ['minimalist', 'bright colors'],
                'competitors': ['brandA', 'brandB'],
                'target_audience': '18-35 age group'
            },
            user_id=user_id
        )
        self.stdout.write(f'  Created Creation: {creation1.uuid}')
        
        creation2 = Creation.objects.create(
            brand=brand,
            title='Holiday Campaign Video',
            post_type='reel',
            status='in_progress',
            platforms='instagram,tiktok',
            post_tone='festive, heartwarming',
            original_prompt='Create a festive video for the holiday season',
            user_id=user_id
        )
        self.stdout.write(f'  Created Creation: {creation2.uuid}')
        
        creation3 = Creation.objects.create(
            brand=brand2,
            title='Fashion Week Special',
            post_type='post',
            status='pending',
            platforms='instagram,pinterest',
            post_tone='elegant, sophisticated',
            user_id=user_id
        )
        self.stdout.write(f'  Created Creation: {creation3.uuid}')
        
        # Create Generations
        gen1 = Generation.objects.create(
            creation=creation1,
            media_type='image',
            prompt='Modern product showcase with gradient background, minimal style, high-end commercial photography',
            status='done',
            generation_params={
                'model': 'gemini-2.5-flash',
                'temperature': 0.7
            }
        )
        self.stdout.write(f'  Created Generation: {gen1.uuid}')
        
        gen2 = Generation.objects.create(
            creation=creation1,
            media_type='image',
            prompt='Product detail shot, macro photography, studio lighting',
            status='done',
            generation_params={
                'model': 'gemini-2.5-flash',
                'temperature': 0.5
            }
        )
        self.stdout.write(f'  Created Generation: {gen2.uuid}')
        
        # Create child generation (variation)
        gen3 = Generation.objects.create(
            creation=creation1,
            parent=gen1,
            media_type='image',
            prompt='Add more contrast and warmer tones to the previous image',
            status='done',
            generation_params={
                'model': 'gemini-2.5-flash',
                'temperature': 0.6,
                'variation': True
            }
        )
        self.stdout.write(f'  Created Generation (variation): {gen3.uuid}')
        
        gen4 = Generation.objects.create(
            creation=creation2,
            media_type='video',
            prompt='Holiday scene with snow, warm lights, family gathering',
            status='pending',
            generation_params={
                'model': 'gemini-2.5-flash',
                'temperature': 0.8
            }
        )
        self.stdout.write(f'  Created Generation: {gen4.uuid}')
        
        # Create Media Files
        media1 = MediaFile.objects.create(
            generation=gen1,
            url='https://res.cloudinary.com/example/image/upload/v1234567890/slide1.png',
            file_type='image/png',
            file_size=2048576,
            width=1080,
            height=1080,
            storage_provider='cloudinary'
        )
        self.stdout.write(f'  Created MediaFile: {media1.uuid}')
        
        media2 = MediaFile.objects.create(
            generation=gen2,
            url='https://res.cloudinary.com/example/image/upload/v1234567890/slide2.png',
            file_type='image/png',
            file_size=1892000,
            width=1080,
            height=1080,
            storage_provider='cloudinary'
        )
        self.stdout.write(f'  Created MediaFile: {media2.uuid}')
        
        # Create Posts
        post1 = Post.objects.create(
            brand=brand,
            creation=creation1,
            copy='Introducing our Summer Collection! 🌞✨\n\nGet ready to elevate your style with our latest products.\n\n#SummerVibes #NewCollection #TechCorp',
            status='published',
            executed_at='2026-03-05T14:30:00Z',
            post_type='carousel',
            platforms='instagram,linkedin',
            likes=1250,
            comments=45,
            shares=12,
            reach=15600,
            engagement_rate=8.45,
            user_id=user_id
        )
        self.stdout.write(f'  Created Post: {post1.uuid}')
        
        post2 = Post.objects.create(
            brand=brand,
            creation=creation1,
            copy='Behind the scenes of our Summer shoot! 📸\n\nSwipe to see the magic happen.\n\n#BehindTheScenes #SummerCollection',
            status='scheduled',
            scheduled_date='2026-03-15T10:00:00Z',
            post_type='post',
            platforms='instagram',
            likes=0,
            comments=0,
            shares=0,
            reach=0,
            engagement_rate=0.0,
            user_id=user_id
        )
        self.stdout.write(f'  Created Post: {post2.uuid}')
        
        post3 = Post.objects.create(
            brand=brand2,
            creation=creation3,
            copy='Fashion Week is here! 👗✨\n\nStay tuned for exclusive looks from the runway.\n\n#FashionWeek #Runway #Style',
            status='draft',
            post_type='reel',
            platforms='instagram,tiktok',
            user_id=user_id
        )
        self.stdout.write(f'  Created Post: {post3.uuid}')
        
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
                engagement_rate=5.5 + (i * 0.1),
                metrics={
                    'profile_visits': 1200 + i * 20,
                    'website_clicks': 150 + i * 5
                }
            )
        self.stdout.write(f'  Created 30 PlatformInsight records for Instagram')
        
        for i in range(30):
            insight_date = date(2026, 2, 1) + timedelta(days=i)
            PlatformInsight.objects.create(
                brand=brand,
                platform='linkedin',
                date=insight_date,
                followers=5000 + (i * 20),
                impressions=25000 + (i * 500),
                reach=15000 + (i * 300),
                engagement_rate=3.2 + (i * 0.05),
                metrics={
                    'clicks': 800 + i * 10,
                    'shares': 50 + i * 2
                }
            )
        self.stdout.write(f'  Created 30 PlatformInsight records for LinkedIn')
        
        self.stdout.write(self.style.SUCCESS('\n[SUCCESS] Dummy data created successfully!'))
        self.stdout.write('\nTest Credentials:')
        self.stdout.write(f'  User ID: {user_id}')
        self.stdout.write(f'  Tenant ID: {tenant_id}')
        self.stdout.write(f'\nSample Brand UUID: {brand.uuid}')
        self.stdout.write(f'Sample Creation UUID: {creation1.uuid}')
