import json

from ...state import BrandDNAState


def preprocessing_node(state: BrandDNAState):
    if state.get("error"):
        return state

    result = state["scraper_result"]
    metadata = result.get("metadata", {})

    structured_data = {
        "title": metadata.get("title", ""),
        "description": metadata.get("description", ""),
        "logo_url": metadata.get("logo", ""),
        "potential_logo_urls": metadata.get("logo_candidates", []),
        "extracted_hex_colors": result.get("extracted_colors", []),
        "extracted_font_families": result.get("extracted_fonts", []),
        "raw_text_snippet": result.get("clean_text", ""),
    }

    return {"preprocessed_data": json.dumps(structured_data, indent=2)}
