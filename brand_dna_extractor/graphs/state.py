from typing import TypedDict, Optional, Dict, Any


class BrandDNAState(TypedDict):
    input_url: str
    user_id: Optional[str]
    tenant_id: Optional[str]
    scraper_result: Dict[str, Any]
    preprocessed_data: str
    llm_output: Dict[str, Any]
    brand_id: Optional[str]
    db_saved: bool
    error: Optional[str]
