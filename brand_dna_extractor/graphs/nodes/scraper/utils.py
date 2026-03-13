import re
import json
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
        from collections import Counter
        hex_colors = re.findall(r'#(?:[0-9a-fA-F]{3}){1,2}\b', html_content)
        counts = Counter(c.upper() for c in hex_colors)
        return [color for color, _ in counts.most_common(10)]

    @staticmethod
    def extract_font_families(html_content):
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

        title = soup.title.string.strip() if soup.title and soup.title.string else ""
        description = ""
        desc_tag = (
            soup.find('meta', attrs={'name': 'description'})
            or soup.find('meta', attrs={'property': 'og:description'})
        )
        if desc_tag:
            description = desc_tag.get('content', '')

        # Collect potential logos from various strategies
        logo_candidates = []

        # Strategy 1: Schema.org JSON-LD (Usually the most reliable)
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                if isinstance(data, dict):
                    data = [data]
                for item in (data or []):
                    # Check nested @graph if present (Common in WordPress/Yoast)
                    items_to_check = [item]
                    if '@graph' in item:
                        items_to_check.extend(item['@graph'])
                    
                    for sub_item in items_to_check:
                        if sub_item.get('@type') in ['Organization', 'Brand', 'LocalBusiness']:
                            schema_logo = sub_item.get('logo')
                            if isinstance(schema_logo, dict):
                                schema_logo = schema_logo.get('url')
                            if schema_logo and isinstance(schema_logo, str):
                                abs_url = BrandScraperUtility.to_absolute_url(base_url, schema_logo)
                                logo_candidates.append((100, abs_url)) # High priority
            except Exception:
                continue

        # Strategy 2: OpenGraph image (fallback)
        og_img_tag = soup.find('meta', property='og:image')
        if og_img_tag and og_img_tag.get('content'):
            og_img = BrandScraperUtility.to_absolute_url(base_url, og_img_tag.get('content'))
            logo_candidates.append((30, og_img))

        # Strategy 3: Scored <img> tags
        for img in soup.find_all('img'):
            src = img.get('src') or img.get('data-src') or img.get('srcset')
            if src:
                # Handle srcset if present
                if ',' in src:
                    src = src.split(',')[0].strip().split(' ')[0]
                
                abs_url = BrandScraperUtility.to_absolute_url(base_url, src)
                score = BrandScraperUtility.score_logo_url(abs_url)
                
                # Boost if in header or has logo class/id
                parent_attrs = str(img.parent.get('class', [])) + str(img.parent.get('id', ''))
                if 'header' in parent_attrs.lower() or 'brand' in parent_attrs.lower():
                    score += 20
                
                if 'logo' in (img.get('alt') or '').lower():
                    score += 60
                
                if score > 0:
                    logo_candidates.append((score, abs_url))

        # Strategy 4: Favicon as desperate fallback
        icon_link = soup.find("link", rel=lambda x: x and 'icon' in x.lower())
        if icon_link and icon_link.get('href'):
            favicon = BrandScraperUtility.to_absolute_url(base_url, icon_link.get('href'))
            logo_candidates.append((5, favicon))

        # Sort candidates and pick best
        logo_candidates.sort(reverse=True, key=lambda x: x[0])
        
        # Deduplicate while preserving order
        seen = set()
        clean_candidates = []
        for score, url in logo_candidates:
            if url not in seen and url.startswith('http'):
                clean_candidates.append(url)
                seen.add(url)

        best_logo = clean_candidates[0] if clean_candidates else ""

        return {
            "title": title,
            "description": description,
            "logo": best_logo,
            "logo_candidates": clean_candidates[:10],
            "favicon": clean_candidates[-1] if clean_candidates else "",
        }

    @classmethod
    def scrape_url(cls, url):
        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/91.0.4472.124 Safari/537.36"
                )
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            html_content = response.text

            metadata = cls.extract_metadata(html_content, url)
            colors = cls.extract_colors(html_content)
            fonts = cls.extract_font_families(html_content)

            soup = BeautifulSoup(html_content, 'html.parser')
            for tag in soup(["script", "style", "nav", "footer"]):
                tag.extract()
            clean_text = soup.get_text(separator=' ', strip=True)[:3000]

            return {
                "success": True,
                "url": url,
                "raw_html": html_content,
                "clean_text": clean_text,
                "metadata": metadata,
                "extracted_colors": colors,
                "extracted_fonts": fonts,
            }
        except Exception as e:
            return {"success": False, "error": str(e), "url": url}
