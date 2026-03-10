from ...state import BrandDNAState
from .utils import BrandScraperUtility


def scraper_node(state: BrandDNAState):
    result = BrandScraperUtility.scrape_url(state["input_url"])
    if not result.get("success"):
        return {"scraper_result": result, "error": result.get("error")}
    return {"scraper_result": result, "error": None}
