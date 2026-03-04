import urllib.request
from langchain_core.tools import tool


@tool
def fetch_brand_website(url: str) -> str:
    """Fetches the text content of a brand's website to help extract brand DNA.
    Use this when a URL is provided as part of the brand input."""
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            html = response.read().decode("utf-8", errors="ignore")

        # Strip tags with a simple approach to get readable text
        import re
        text = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL)
        text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()

        return text[:4000]
    except Exception as e:
        return f"Could not fetch {url}: {e}"


tools = [fetch_brand_website]
