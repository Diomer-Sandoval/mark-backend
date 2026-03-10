import re
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

class BrandScraperUtility:
    @staticmethod
    def to_absolute_url(base_url, url):
        if not url:
            return ""
        return urljoin(base_url, url)

    @staticmethod
    def score_logo_url(url):
        score = 0
        url_lower = url.lower()
        if 'logo' in url_lower:
            score += 50
        if url_lower.endswith('.svg'):
            score += 30
        elif url_lower.endswith('.png'):
            score += 20
        if 'transparent' in url_lower:
            score += 10
        if 'favicon' in url_lower:
            score -= 20
        return score

    @staticmethod
    def extract_colors(html_content):
        # Extract hex colors
        hex_colors = re.findall(r'#(?:[0-9a-fA-F]{3}){1,2}\b', html_content)
        # Filter and count frequencies, return top unique colors
        from collections import Counter
        counts = Counter(c.upper() for c in hex_colors)
        return [color for color, _ in counts.most_common(10)]

    @staticmethod
    def extract_font_families(html_content):
        # Extract font families from inline styles and style tags
        fonts = []
        soup = BeautifulSoup(html_content, 'html.parser')
        for style in soup.find_all('style'):
            if style.string:
                f_matches = re.findall(r'font-family:\s*([^;}]+)', style.string)
                fonts.extend([f.strip().strip('"\'') for f in f_matches])
        return list(set(fonts))

    @staticmethod
    def extract_metadata(html_content, base_url):
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Meta tags
        title = soup.title.string.strip() if soup.title and soup.title.string else ""
        description = ""
        desc_tag = soup.find('meta', attrs={'name': 'description'}) or soup.find('meta', attrs={'property': 'og:description'})
        if desc_tag:
            description = desc_tag.get('content', '')
            
        # Strategy 1: Find best logo from standard <img> tags
        img_tags = soup.find_all('img')
        logos = []
        for img in img_tags:
            src = img.get('src') or img.get('data-src') # Also capture lazy-loaded images
            if src:
                abs_url = BrandScraperUtility.to_absolute_url(base_url, src)
                score = BrandScraperUtility.score_logo_url(abs_url)
                
                # Check alt-text as an extra heuristic
                alt_text = (img.get('alt') or '').lower()
                if 'logo' in alt_text:
                    score += 60
                
                if score > 0:
                    logos.append((score, abs_url))
                    
        logos.sort(reverse=True, key=lambda x: x[0])
        best_logo = logos[0][1] if logos else ""
        
        # Strategy 2: Check OpenGraph meta tags if no strong logo found
        if not best_logo or logos[0][0] < 50:
            og_img_tag = soup.find('meta', property='og:image')
            if og_img_tag and og_img_tag.get('content'):
                og_img = BrandScraperUtility.to_absolute_url(base_url, og_img_tag.get('content'))
                # Replace if we had nothing, or if OG image strongly indicates it's the brand logo
                if not best_logo or BrandScraperUtility.score_logo_url(og_img) > 20: 
                    best_logo = og_img
                    
        # Strategy 3: Check Schema.org JSON-LD definitions
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                import json
                data = json.loads(script.string)
                # Handle cases where schema is an array
                if isinstance(data, dict):
                    data = [data]
                for item in (data or []):
                    if item.get('@type') in ['Organization', 'Brand', 'LocalBusiness']:
                        schema_logo = item.get('logo')
                        if isinstance(schema_logo, dict):
                            schema_logo = schema_logo.get('url')
                        if schema_logo and isinstance(schema_logo, str):
                            best_logo = BrandScraperUtility.to_absolute_url(base_url, schema_logo)
                            break
            except:
                continue
        
        # Find favicon
        favicon = ""
        icon_link = soup.find("link", rel=lambda x: x and 'icon' in x.lower())
        if icon_link and icon_link.get('href'):
            favicon = BrandScraperUtility.to_absolute_url(base_url, icon_link.get('href'))
            
        return {
            "title": title,
            "description": description,
            "logo": best_logo,
            "favicon": favicon,
        }

    @classmethod
    def scrape_url(cls, url):
        try:
            # We add headers to mimic a browser
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            html_content = response.text
            
            metadata = cls.extract_metadata(html_content, url)
            colors = cls.extract_colors(html_content)
            fonts = cls.extract_font_families(html_content)
            
            # Additional cleanup of HTML to get clean text for LLM
            soup = BeautifulSoup(html_content, 'html.parser')
            # Remove scripts and styles
            for script in soup(["script", "style", "nav", "footer"]):
                script.extract()
            text = soup.get_text(separator=' ', strip=True)
            # Take first ~3000 chars to avoid overwhelming context
            clean_text = text[:3000]
            
            return {
                "success": True,
                "url": url,
                "raw_html": html_content,
                "clean_text": clean_text,
                "metadata": metadata,
                "extracted_colors": colors,
                "extracted_fonts": fonts
            }
        except Exception as e:
            return {"success": False, "error": str(e), "url": url}
