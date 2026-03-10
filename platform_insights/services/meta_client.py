import logging
import requests
from datetime import timedelta
from django.utils.timezone import now
from creation_studio.models_core import Brand, PlatformInsight, Post
from django.utils.dateparse import parse_datetime
from .meta_auth import META_ACCESS_TOKEN, INSTAGRAM_BUSINESS_ACCOUNT_ID, FACEBOOK_PAGE_ID

logger = logging.getLogger(__name__)

class MetaInsightService:
    BASE_URL = "https://graph.facebook.com/v24.0"

    def __init__(self, meta_token=META_ACCESS_TOKEN, 
                 ig_account_id=INSTAGRAM_BUSINESS_ACCOUNT_ID, fb_page_id=FACEBOOK_PAGE_ID):
        self.token = meta_token
        self.ig_account_id = ig_account_id
        self.fb_page_id = fb_page_id
        self.session = requests.Session()

    def fetch_instagram_insights(self, days=30):
        """Fetch insights for the last `days` days from Instagram."""
        if not self.token or not self.ig_account_id:
            logger.error("Missing Meta Access Token or Account ID.")
            raise ValueError("Missing Meta Access Token or Account I")

        end_date = now()
        start_date = end_date - timedelta(days=days)
        
        since_ts = int(start_date.timestamp())
        until_ts = int(end_date.timestamp())

        # First request: Time-series metrics (reach)
        url = f"{self.BASE_URL}/{self.ig_account_id}/insights"
        reach_params = {
            "metric": "reach",
            "period": "day",
            "since": since_ts,
            "until": until_ts,
            "access_token": self.token
        }
        
        reach_response = self.session.get(url, params=reach_params)
        
        if reach_response.status_code != 200:
            error_msg = f"Error fetching Instagram reach insights: {reach_response.text}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Second request: Lifetime/Total metrics (profile_views) that require metric_type=total_value
        pv_params = {
            "metric": "profile_views",
            "metric_type": "total_value",
            "period": "day",
            "since": since_ts,
            "until": until_ts,
            "access_token": self.token
        }

        pv_response = self.session.get(url, params=pv_params)
        
        if pv_response.status_code != 200:
            error_msg = f"Error fetching Instagram profile_views: {pv_response.text}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        reach_data = reach_response.json().get('data', [])
        pv_data = pv_response.json().get('data', [])
        
        data = reach_data + pv_data
        
        daily_metrics = {}
        for metric_item in data:
            metric_name = metric_item['name']
            for value_item in metric_item.get('values', []):
                date_str = value_item['end_time'][:10]
                if date_str not in daily_metrics:
                    daily_metrics[date_str] = {
                        "platform": "instagram",  
                        "date": date_str,
                        "impressions": 0,
                        "reach": 0,
                        "followers": 0,
                        "engagement_rate": 0.0,
                        "_engagements": 0
                    }
                
                if metric_name == 'reach':
                    daily_metrics[date_str]['reach'] = value_item['value']
                    # Using reach as impressions fallback since impressions is no longer a valid metric
                    daily_metrics[date_str]['impressions'] = value_item['value']
                elif metric_name == 'profile_views':
                    daily_metrics[date_str]['_engagements'] = value_item['value']

        for metric in daily_metrics.values():
            reach = metric.get("reach", 0)
            engagements = metric.pop("_engagements", 0)
            if reach and reach > 0:
                metric["engagement_rate"] = (engagements / reach) * 100
            else:
                metric["engagement_rate"] = 0.0

        return list(daily_metrics.values())

    def fetch_facebook_insights(self, days=28):
        """Fetch insights for Facebook Page."""
        if not self.token or not self.fb_page_id:
            logger.error("Missing Meta Access Token or Page ID.")
            raise ValueError("Missing Meta Access Token or Page ID.")

        end_date = now()
        start_date = end_date - timedelta(days=days)

        since_ts = int(start_date.timestamp())
        until_ts = int(end_date.timestamp())

        # 1. Fetch Follower count (Global info from Graph API)
        url_profile = f"{self.BASE_URL}/{self.fb_page_id}"
        profile_params = {
            "fields": "followers_count",
            "access_token": self.token
        }
        profile_response = self.session.get(url_profile, params=profile_params)
        
        followers = 0
        if profile_response.status_code == 200:
            followers = profile_response.json().get('followers_count', 0)

        # 2. Fetch Time-series insights
        url = f"{self.BASE_URL}/{self.fb_page_id}/insights"
        
        params = {
            "metric": "page_views_total,page_impressions_unique,page_post_engagements",
            "period": "day",
            "since": since_ts,
            "until": until_ts,
            "access_token": self.token
        }

        response = self.session.get(url, params=params)
        if response.status_code != 200:
            error_msg = f"Error fetching Facebook insights: {response.text}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        data = response.json().get('data', [])
        daily_metrics = {}
        for metric_item in data:
            metric_name = metric_item['name']
            for value_item in metric_item.get('values', []):
                date_str = value_item['end_time'][:10]
                if date_str not in daily_metrics:
                    daily_metrics[date_str] = {
                        "platform": "facebook", 
                        "date": date_str,
                        "impressions": 0,
                        "reach": 0,
                        "followers": followers, # Current count applied globally
                        "engagement_rate": 0.0,
                        "_engagements": 0
                    }
                
                if metric_name == "page_views_total":
                    daily_metrics[date_str]["impressions"] = value_item['value']
                elif metric_name == "page_impressions_unique":
                    daily_metrics[date_str]["reach"] = value_item['value'] 
                elif metric_name == "page_post_engagements":
                    daily_metrics[date_str]["_engagements"] = value_item['value']

        for metric in daily_metrics.values():
            reach = metric.get("reach", 0)
            engagements = metric.pop("_engagements", 0)
            if reach and reach > 0:
                metric["engagement_rate"] = (engagements / reach) * 100
            else:
                metric["engagement_rate"] = 0.0

        return list(daily_metrics.values())

    def sync_insights_for_brand(self, brand, days=30):
        """Sync insights for a single brand."""
        logger.info(f"Syncing insights for brand: {brand.name}")
        
        ig_insights = self.fetch_instagram_insights(days=days)
        fb_insights = self.fetch_facebook_insights(days=days)
        
        all_insights = ig_insights + fb_insights
        
        for insight in all_insights:
            PlatformInsight.objects.update_or_create(
                brand=brand,  
                platform=insight['platform'],
                date=insight['date'],
                defaults={
                    'impressions': insight['impressions'],
                    'reach': insight['reach'],
                    'followers': insight.get('followers', 0),
                    'engagement_rate': insight['engagement_rate']
                }
            )
        
        return len(ig_insights), len(fb_insights)

    def sync_all_active_brands(self, days=30):
        """Iterate through all active brands and sync insights."""
        active_brands = Brand.objects.filter(is_active=True)
        for brand in active_brands:
            self.sync_insights_for_brand(brand, days=days)
            self.sync_external_posts_for_brand(brand)

    def fetch_instagram_posts(self, limit=50):
        """Fetch latest posts from Instagram Platform."""
        if not self.token or not self.ig_account_id:
            logger.error("Missing Meta Access Token or Account ID.")
            return []
            
        url = f"{self.BASE_URL}/{self.ig_account_id}/media"
        params = {
            "fields": "id,caption,media_type,timestamp,like_count,comments_count,permalink",
            "access_token": self.token,
            "limit": limit
        }
        
        response = self.session.get(url, params=params)
        if response.status_code != 200:
            logger.error(f"Error fetching Instagram posts: {response.text}")
            return []
            
        return response.json().get('data', [])

    def fetch_facebook_posts(self, limit=50):
        """Fetch latest posts from Facebook Page."""
        if not self.token or not self.fb_page_id:
            logger.error("Missing Meta Access Token or Page ID.")
            return []
            
        url = f"{self.BASE_URL}/{self.fb_page_id}/posts"
        params = {
            "fields": "id,message,created_time,permalink_url,likes.summary(true),comments.summary(true),shares",
            "access_token": self.token,
            "limit": limit
        }
        
        response = self.session.get(url, params=params)
        if response.status_code != 200:
            logger.error(f"Error fetching Facebook posts: {response.text}")
            return []
            
        return response.json().get('data', [])

    def sync_external_posts_for_brand(self, brand, limit=50):
        """Fetch real posts from Facebook & Instagram, syncing them into Postgres."""
        ig_posts = self.fetch_instagram_posts(limit=limit)
        fb_posts = self.fetch_facebook_posts(limit=limit)
        
        synced_count = 0
        
        # Instagram Posts
        for p in ig_posts:
            meta_id = p.get('id')
            if not meta_id: continue
            
            existing = Post.objects.filter(brand=brand, metrics__meta_id=meta_id).first()
            likes = p.get('like_count', 0)
            comments = p.get('comments_count', 0)
            
            if existing:
                existing.likes = likes
                existing.comments = comments
                existing.save(update_fields=['likes', 'comments'])
            else:
                caption = p.get('caption', '')
                media_type = p.get('media_type', '')
                timestamp_str = p.get('timestamp')
                permalink = p.get('permalink', '')
                
                post_type = 'post'
                if media_type == 'VIDEO':
                    post_type = 'reel'
                elif media_type == 'CAROUSEL_ALBUM':
                    post_type = 'carousel'
                    
                executed_at = parse_datetime(timestamp_str) if timestamp_str else now()
                
                Post.objects.create(
                    brand=brand,
                    creation=None,
                    copy=caption,
                    status='published',
                    executed_at=executed_at,
                    post_type=post_type,
                    platforms='instagram',
                    likes=likes,
                    comments=comments,
                    metrics={'meta_id': meta_id, 'permalink': permalink}
                )
                synced_count += 1
                
        # Facebook Posts
        for p in fb_posts:
            meta_id = p.get('id')
            if not meta_id: continue
            
            existing = Post.objects.filter(brand=brand, metrics__meta_id=meta_id).first()
            likes = p.get('likes', {}).get('summary', {}).get('total_count', 0)
            comments = p.get('comments', {}).get('summary', {}).get('total_count', 0)
            
            shares = 0
            if p.get('shares'):
                 shares = p.get('shares', {}).get('count', 0)
            
            if existing:
                existing.likes = likes
                existing.comments = comments
                existing.shares = shares
                existing.save(update_fields=['likes', 'comments', 'shares'])
            else:
                message = p.get('message', '')
                timestamp_str = p.get('created_time')
                permalink = p.get('permalink_url', '')
                
                executed_at = parse_datetime(timestamp_str) if timestamp_str else now()
                
                Post.objects.create(
                    brand=brand,
                    creation=None,
                    copy=message,
                    status='published',
                    executed_at=executed_at,
                    post_type='post',
                    platforms='facebook',
                    likes=likes,
                    comments=comments,
                    shares=shares,
                    metrics={'meta_id': meta_id, 'permalink': permalink}
                )
                synced_count += 1
                
        return synced_count
