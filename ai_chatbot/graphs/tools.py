"""
Tools for MARK AI Agents.

This module provides tools for:
- Database queries (brands, posts, analytics, etc.)
- Web search (trends, competitors, research) via OpenAI gpt-4o-search-preview
- Template search
- Image generation via DALL-E 3
"""

import json
import os
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
import requests
from django.db.models import Q, Avg, Sum, Count, Max, Min
from django.db.models.functions import TruncDate

# Import models
from brand_dna_extractor.models import Brand, BrandDNA
from creation_studio.models import Creation, Generation
from platform_insights.models import Post, PlatformInsight
from content_templates.models import TemplateDocument
from content_templates.services.search import TemplateSearchService
from content_templates.services.embedding import TemplateEmbeddingService


class EmbeddingService:
    """Wrapper for TemplateEmbeddingService for generic embedding needs."""
    
    def __init__(self):
        self.service = TemplateEmbeddingService()
    
    def get_embedding(self, text: str) -> list:
        """Get embedding for text."""
        return self.service.embed_text(text)


# ============================================================================
# WEB SEARCH TOOLS
# ============================================================================

class WebSearchInput(BaseModel):
    """Input for web search tool."""
    query: str = Field(description="Search query")
    num_results: int = Field(default=5, description="Number of results to return")


def _openai_web_search(query: str) -> tuple[str, list]:
    """
    Perform a live web search using OpenAI gpt-4o-search-preview.
    Returns (text_content, citations_list).
    """
    from openai import OpenAI
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    model = os.environ.get("OPENAI_SEARCH_MODEL", "gpt-4o-search-preview")

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": query}],
    )

    message = response.choices[0].message
    text = message.content or ""

    # Extract URL citations from annotations
    citations = []
    annotations = getattr(message, "annotations", None) or []
    for ann in annotations:
        ann_type = getattr(ann, "type", "")
        if ann_type == "url_citation":
            url_cit = getattr(ann, "url_citation", None)
            if url_cit:
                citations.append({
                    "title": getattr(url_cit, "title", ""),
                    "url": getattr(url_cit, "url", ""),
                })

    return text, citations


class WebSearchTool(BaseTool):
    """Tool for searching the web for current information via OpenAI Web Search."""

    name: str = "web_search"
    description: str = """Search the web for current information about trends, competitors, or any topic.
    Use this when you need up-to-date information not available in the database."""
    args_schema: Type[BaseModel] = WebSearchInput

    def _run(self, query: str, num_results: int = 5) -> str:
        """Execute live web search using OpenAI gpt-4o-search-preview."""
        try:
            text, citations = _openai_web_search(query)

            result_parts = [text]
            if citations:
                result_parts.append("\n\nSources:")
                for i, c in enumerate(citations[:num_results], 1):
                    result_parts.append(f"{i}. {c.get('title', 'Source')} — {c.get('url', '')}")

            return "\n".join(result_parts) if result_parts else "No results found."

        except Exception as e:
            return f"Search error: {str(e)}. The MARK AI will answer from available knowledge."


class TrendsSearchInput(BaseModel):
    """Input for trends search."""
    topic: str = Field(description="Topic or industry to search trends for")
    timeframe: str = Field(default="today 12-m", description="Time period for trends")


class TrendsSearchTool(BaseTool):
    """Tool for searching current trends via OpenAI Web Search."""

    name: str = "search_trends"
    description: str = """Search for current trends in a specific topic or industry.
    Use this to find trending topics, hashtags, or content ideas."""
    args_schema: Type[BaseModel] = TrendsSearchInput

    def _run(self, topic: str, timeframe: str = "today 12-m") -> str:
        """Search for trends using OpenAI gpt-4o-search-preview."""
        try:
            query = (
                f"What are the top social media content trends for '{topic}' right now in 2026? "
                f"Include trending formats, viral examples, engagement tactics, and platform-specific trends. "
                f"Focus on actionable insights for marketers."
            )
            text, citations = _openai_web_search(query)

            result_parts = [text]
            if citations:
                result_parts.append("\n\nSources:")
                for i, c in enumerate(citations[:6], 1):
                    result_parts.append(f"{i}. {c.get('title', 'Source')} — {c.get('url', '')}")

            return "\n".join(result_parts) if result_parts else "No trend data found."

        except Exception as e:
            return f"Trends search error: {str(e)}. Answering from available knowledge."


class CompetitorResearchInput(BaseModel):
    """Input for competitor research."""
    competitor_name: str = Field(description="Name of competitor to research")
    platform: Optional[str] = Field(default=None, description="Specific platform (instagram, linkedin, etc.)")


class CompetitorResearchTool(BaseTool):
    """Tool for researching competitor content and strategy via OpenAI Web Search."""

    name: str = "research_competitor"
    description: str = """Research a competitor's content strategy, messaging, and positioning.
    Use this to analyze competitors and find differentiation opportunities."""
    args_schema: Type[BaseModel] = CompetitorResearchInput

    def _run(self, competitor_name: str, platform: Optional[str] = None) -> str:
        """Research competitor using OpenAI gpt-4o-search-preview."""
        try:
            platform_clause = f" on {platform}" if platform else " across social media platforms"
            query = (
                f"Analyze {competitor_name}'s content marketing strategy{platform_clause}. "
                f"Include: their main content themes, messaging style, content formats they use, "
                f"what gets high engagement, their brand positioning, and any content gaps or "
                f"differentiation opportunities for competitors."
            )
            text, citations = _openai_web_search(query)

            result_parts = [f"## Competitor Research: {competitor_name}\n", text]
            if citations:
                result_parts.append("\n\nSources:")
                for i, c in enumerate(citations[:6], 1):
                    result_parts.append(f"{i}. {c.get('title', 'Source')} — {c.get('url', '')}")

            return "\n".join(result_parts) if result_parts else "No competitor data found."

        except Exception as e:
            return f"Competitor research error: {str(e)}. Answering from available knowledge."


# ============================================================================
# IMAGE GENERATION TOOL
# ============================================================================

class ImageGenerationInput(BaseModel):
    """Input for DALL-E 3 image generation."""
    prompt: str = Field(description="Detailed image generation prompt describing the visual")
    size: str = Field(
        default="1024x1024",
        description="Image dimensions: '1024x1024' (square), '1792x1024' (landscape), '1024x1792' (portrait)",
    )
    quality: str = Field(
        default="standard",
        description="Image quality: 'standard' (faster) or 'hd' (more detail)",
    )


class ImageGenerationTool(BaseTool):
    """Tool for generating marketing images via DALL-E 3."""

    name: str = "generate_image"
    description: str = (
        "Generate a high-quality marketing image using DALL-E 3. "
        "Use when the user wants a visual, image, or graphic created for their marketing content. "
        "Always write a detailed, descriptive prompt for best results."
    )
    args_schema: Type[BaseModel] = ImageGenerationInput

    def _run(self, prompt: str, size: str = "1024x1024", quality: str = "standard") -> dict:
        """Generate an image with DALL-E 3."""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            model = os.environ.get("OPENAI_IMAGE_MODEL", "dall-e-3")

            valid_sizes = {"1024x1024", "1792x1024", "1024x1792"}
            if size not in valid_sizes:
                size = "1024x1024"
            if quality not in {"standard", "hd"}:
                quality = "standard"

            response = client.images.generate(
                model=model,
                prompt=prompt,
                size=size,
                quality=quality,
                n=1,
            )

            image_data = response.data[0]
            return {
                "success": True,
                "url": image_data.url,
                "revised_prompt": getattr(image_data, "revised_prompt", prompt),
                "size": size,
                "quality": quality,
                "model": model,
                "note": "Image URL expires after 1 hour. Download/save if you need to keep it.",
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "url": None,
                "revised_prompt": None,
            }


# ============================================================================
# DATABASE QUERY TOOLS
# ============================================================================

class GetBrandInfoInput(BaseModel):
    """Input for getting brand information."""
    brand_id: Optional[str] = Field(default=None, description="Brand UUID (optional, uses context if not provided)")


class GetBrandInfoTool(BaseTool):
    """Tool for retrieving brand information from the database."""
    
    name: str = "get_brand_info"
    description: str = """Get detailed information about a brand including DNA, identity, and metadata.
    Use this when the user asks about their brand or when you need brand context."""
    args_schema: Type[BaseModel] = GetBrandInfoInput
    
    def _run(self, brand_id: Optional[str] = None) -> str:
        """Get brand information from database."""
        try:
            if not brand_id:
                return "No brand ID provided. Please specify a brand or ensure you're working in a brand context."
            
            brand = Brand.objects.filter(uuid=brand_id).first()
            if not brand:
                return f"Brand with ID '{brand_id}' not found."
            
            # Get brand DNA if available
            dna_info = {}
            if hasattr(brand, 'dna') and brand.dna:
                dna = brand.dna
                dna_info = {
                    "primary_color": dna.primary_color,
                    "secondary_color": dna.secondary_color,
                    "accent_color": dna.accent_color,
                    "font_body": dna.font_body_family,
                    "font_headings": dna.font_headings_family,
                    "voice_tone": dna.voice_tone,
                    "keywords": dna.keywords,
                    "description": dna.description,
                }
            
            brand_data = {
                "uuid": brand.uuid,
                "name": brand.name,
                "industry": brand.industry,
                "page_url": brand.page_url,
                "is_active": brand.is_active,
                "created_at": str(brand.created_at),
                "dna": dna_info,
            }
            
            return json.dumps(brand_data, indent=2)
            
        except Exception as e:
            return f"Error retrieving brand info: {str(e)}"


class GetUserBrandsInput(BaseModel):
    """Input for getting user's brands."""
    user_id: str = Field(description="User ID to fetch brands for")


class GetUserBrandsTool(BaseTool):
    """Tool for retrieving all brands for a user."""
    
    name: str = "get_user_brands"
    description: str = """Get all brands belonging to a user.
    Use this when the user asks about their brands, or when you need to find the user's brand_id.
    Call this first if no brand_id is provided in the context."""
    args_schema: Type[BaseModel] = GetUserBrandsInput
    
    def _run(self, user_id: str) -> str:
        """Get all brands for a user."""
        try:
            brands = Brand.objects.filter(user_id=user_id, is_active=True)
            
            if not brands.exists():
                return json.dumps({
                    "count": 0,
                    "message": "No brands found. User needs to create a brand first.",
                    "brands": []
                })
            
            brand_list = []
            for brand in brands:
                brand_list.append({
                    "uuid": brand.uuid,
                    "name": brand.name,
                    "industry": brand.industry,
                    "created_at": str(brand.created_at),
                })
            
            return json.dumps({
                "count": len(brand_list),
                "message": f"Found {len(brand_list)} brand(s)",
                "brands": brand_list,
                "first_brand_id": brand_list[0]["uuid"] if brand_list else None
            }, indent=2)
            
        except Exception as e:
            return f"Error retrieving brands: {str(e)}"


class GetCreationsInput(BaseModel):
    """Input for getting creations."""
    brand_id: Optional[str] = Field(default=None, description="Filter by brand ID")
    status: Optional[str] = Field(default=None, description="Filter by status")
    limit: int = Field(default=10, description="Maximum number of results")


class GetCreationsTool(BaseTool):
    """Tool for retrieving content creations/projects."""
    
    name: str = "get_creations"
    description: str = """Get content creation projects for a brand.
    Use this when the user asks about their content projects or campaigns."""
    args_schema: Type[BaseModel] = GetCreationsInput
    
    def _run(self, brand_id: Optional[str] = None, status: Optional[str] = None, limit: int = 10) -> str:
        """Get creations from database."""
        try:
            queryset = Creation.objects.all()
            
            if brand_id:
                queryset = queryset.filter(brand_id=brand_id)
            if status:
                queryset = queryset.filter(status=status)
            
            queryset = queryset.order_by('-created_at')[:limit]
            
            if not queryset.exists():
                return "No creations found matching the criteria."
            
            creations = []
            for c in queryset:
                creations.append({
                    "uuid": c.uuid,
                    "title": c.title,
                    "post_type": c.post_type,
                    "status": c.status,
                    "platforms": c.platforms,
                    "post_tone": c.post_tone,
                    "created_at": str(c.created_at),
                    "generations_count": c.generations.count(),
                })
            
            return json.dumps(creations, indent=2)
            
        except Exception as e:
            return f"Error retrieving creations: {str(e)}"


class GetPostsInput(BaseModel):
    """Input for getting posts."""
    brand_id: Optional[str] = Field(default=None, description="Filter by brand ID")
    status: Optional[str] = Field(default=None, description="Filter by status")
    limit: int = Field(default=10, description="Maximum number of results")


class GetPostsTool(BaseTool):
    """Tool for retrieving published/scheduled posts."""
    
    name: str = "get_posts"
    description: str = """Get social media posts for a brand.
    Use this when the user asks about their published content, scheduled posts, or posting history.
    If no brand_id is provided, you need to get the user's brands first using get_user_brands."""
    args_schema: Type[BaseModel] = GetPostsInput
    
    def _run(self, brand_id: Optional[str] = None, status: Optional[str] = None, limit: int = 100) -> str:
        """Get posts from database."""
        try:
            queryset = Post.objects.all()
            
            if brand_id:
                queryset = queryset.filter(brand_id=brand_id)
            
            if status:
                queryset = queryset.filter(status=status)
            
            total_count = queryset.count()
            queryset = queryset.order_by('-created_at')[:limit]
            
            if not queryset.exists():
                return json.dumps({
                    "count": 0,
                    "total": total_count,
                    "message": "No posts found for this brand." if brand_id else "No posts found.",
                    "posts": []
                })
            
            posts = []
            for p in queryset:
                copy_preview = p.final_copy[:150] + "..." if p.final_copy and len(p.final_copy) > 150 else (p.final_copy or "")
                posts.append({
                    "uuid": p.uuid,
                    "copy": copy_preview,
                    "status": p.status,
                    "post_type": p.post_type,
                    "scheduled_date": str(p.scheduled_date) if p.scheduled_date else None,
                    "likes": p.likes,
                    "comments": p.comments,
                    "shares": p.shares,
                    "reach": p.reach,
                    "engagement_rate": p.engagement_rate,
                    "created_at": str(p.created_at),
                })
            
            return json.dumps({
                "count": len(posts),
                "total": total_count,
                "message": f"Found {total_count} post(s) total",
                "posts": posts
            }, indent=2)
            
        except Exception as e:
            return f"Error retrieving posts: {str(e)}"


class GetAnalyticsInput(BaseModel):
    """Input for getting analytics."""
    brand_id: str = Field(description="Brand ID to get analytics for")
    platform: Optional[str] = Field(default=None, description="Filter by platform")
    days: int = Field(default=30, description="Number of days to analyze")


class GetAnalyticsTool(BaseTool):
    """Tool for retrieving platform analytics and insights."""
    
    name: str = "get_analytics"
    description: str = """Get platform analytics and performance data for a brand.
    Use this when the user asks about their performance, metrics, or insights."""
    args_schema: Type[BaseModel] = GetAnalyticsInput
    
    def _run(self, brand_id: str, platform: Optional[str] = None, days: int = 30) -> str:
        """Get analytics from database."""
        try:
            from django.utils import timezone
            from datetime import timedelta
            
            start_date = timezone.now().date() - timedelta(days=days)
            
            queryset = PlatformInsight.objects.filter(
                brand_id=brand_id,
                date__gte=start_date
            )
            
            if platform:
                queryset = queryset.filter(platform=platform)
            
            if not queryset.exists():
                return f"No analytics data found for the specified period (last {days} days)."
            
            # Aggregate metrics
            totals = queryset.aggregate(
                total_followers=Sum('followers'),
                total_impressions=Sum('impressions'),
                total_reach=Sum('reach'),
                avg_engagement=Avg('engagement_rate'),
            )
            
            # Platform breakdown
            platform_stats = queryset.values('platform').annotate(
                avg_followers=Avg('followers'),
                total_impressions=Sum('impressions'),
                avg_engagement=Avg('engagement_rate'),
                data_points=Count('id')
            )
            
            # Get latest data
            latest = queryset.order_by('-date')[:7]  # Last 7 data points
            
            analytics = {
                "period_days": days,
                "summary": {
                    "total_impressions": totals['total_impressions'] or 0,
                    "total_reach": totals['total_reach'] or 0,
                    "avg_engagement_rate": round(totals['avg_engagement'] or 0, 2),
                },
                "platform_breakdown": list(platform_stats),
                "recent_data": [
                    {
                        "date": str(item.date),
                        "platform": item.platform,
                        "followers": item.followers,
                        "impressions": item.impressions,
                        "engagement_rate": item.engagement_rate,
                    }
                    for item in latest
                ],
            }
            
            return json.dumps(analytics, indent=2)
            
        except Exception as e:
            return f"Error retrieving analytics: {str(e)}"


class SearchTemplatesInput(BaseModel):
    """Input for template search."""
    query: str = Field(description="Search query for templates")
    template_type: Optional[str] = Field(default=None, description="Filter by template type")
    limit: int = Field(default=5, description="Maximum results")


class SearchTemplatesTool(BaseTool):
    """Tool for searching marketing templates."""
    
    name: str = "search_templates"
    description: str = """Search for marketing templates using semantic similarity.
    Use this when the user is looking for template inspiration or design ideas."""
    args_schema: Type[BaseModel] = SearchTemplatesInput
    
    def _run(self, query: str, template_type: Optional[str] = None, limit: int = 5) -> str:
        """Search templates using embeddings."""
        try:
            # Generate embedding for query
            embedding_service = EmbeddingService()
            query_embedding = embedding_service.get_embedding(query)
            
            # Search templates
            search_service = TemplateSearchService()
            results = search_service.match_documents(query_embedding, match_count=limit * 2)
            
            # Filter by type if specified
            if template_type:
                results = [
                    (doc, score) for doc, score in results
                    if doc.metadata.get('template_type') == template_type or
                    template_type in doc.metadata.get('target_platforms', [])
                ]
            
            results = results[:limit]
            
            if not results:
                return "No matching templates found."
            
            templates = []
            for doc, score in results:
                templates.append({
                    "id": doc.metadata.get('id'),
                    "title": doc.metadata.get('title'),
                    "template_type": doc.metadata.get('template_type'),
                    "design_style": doc.metadata.get('design_style'),
                    "similarity_score": round(score, 3),
                    "preview_url": doc.metadata.get('preview_image_path'),
                    "use_cases": doc.metadata.get('use_cases', []),
                    "industry_fit": doc.metadata.get('industry_fit', []),
                })
            
            return json.dumps(templates, indent=2)
            
        except Exception as e:
            return f"Error searching templates: {str(e)}"


class GetBestPerformingContentInput(BaseModel):
    """Input for getting best performing content."""
    brand_id: str = Field(description="Brand ID to analyze")
    metric: str = Field(default="engagement_rate", description="Metric to rank by")
    limit: int = Field(default=5, description="Number of results")


class GetBestPerformingContentTool(BaseTool):
    """Tool for identifying best performing content."""
    
    name: str = "get_best_performing_content"
    description: str = """Get the best performing posts for a brand.
    Use this when the user asks what content performs best or wants content insights."""
    args_schema: Type[BaseModel] = GetBestPerformingContentInput
    
    def _run(self, brand_id: str, metric: str = "engagement_rate", limit: int = 5) -> str:
        """Get best performing posts."""
        try:
            # Validate metric
            valid_metrics = ['engagement_rate', 'likes', 'comments', 'shares', 'reach']
            if metric not in valid_metrics:
                metric = 'engagement_rate'
            
            posts = Post.objects.filter(
                brand_id=brand_id,
                status='published'
            ).order_by(f'-{metric}')[:limit]
            
            if not posts.exists():
                return "No published posts found for analysis."
            
            results = []
            for p in posts:
                copy_preview = p.final_copy[:150] + "..." if p.final_copy and len(p.final_copy) > 150 else (p.final_copy or "")
                results.append({
                    "uuid": p.uuid,
                    "copy_preview": copy_preview,
                    "post_type": p.post_type,
                    "likes": p.likes,
                    "comments": p.comments,
                    "shares": p.shares,
                    "reach": p.reach,
                    "engagement_rate": p.engagement_rate,
                    "created_at": str(p.created_at),
                })
            
            return json.dumps({
                "ranked_by": metric,
                "top_posts": results
            }, indent=2)
            
        except Exception as e:
            return f"Error analyzing content: {str(e)}"


# ============================================================================
# TOOL COLLECTIONS
# ============================================================================

def get_all_tools() -> List[BaseTool]:
    """Get all available tools."""
    return [
        # Web search tools
        WebSearchTool(),
        TrendsSearchTool(),
        CompetitorResearchTool(),

        # Image generation
        ImageGenerationTool(),

        # Database tools
        GetBrandInfoTool(),
        GetUserBrandsTool(),
        GetCreationsTool(),
        GetPostsTool(),
        GetAnalyticsTool(),
        SearchTemplatesTool(),
        GetBestPerformingContentTool(),
    ]


def get_database_tools() -> List[BaseTool]:
    """Get only database-related tools."""
    return [
        GetBrandInfoTool(),
        GetUserBrandsTool(),
        GetCreationsTool(),
        GetPostsTool(),
        GetAnalyticsTool(),
        SearchTemplatesTool(),
        GetBestPerformingContentTool(),
    ]


def get_research_tools() -> List[BaseTool]:
    """Get research and web search tools."""
    return [
        WebSearchTool(),
        TrendsSearchTool(),
        CompetitorResearchTool(),
    ]
