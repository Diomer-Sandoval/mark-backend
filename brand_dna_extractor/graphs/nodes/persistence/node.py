from django.utils.text import slugify

from ...state import BrandDNAState
from creation_studio.models import Brand, BrandDNA


def persistence_node(state: BrandDNAState):
    if state.get("error"):
        return state

    llm_output = state.get("llm_output", {})
    if not llm_output:
        return {"error": "No LLM output to persist"}

    try:
        brand_dna = BrandDNA.objects.create(
            primary_color=llm_output.get("primary_color", ""),
            secondary_color=llm_output.get("secondary_color", ""),
            accent_color=llm_output.get("accent_color", ""),
            complementary_color=llm_output.get("complementary_color", ""),
            font_body_family=llm_output.get("font_body_family", ""),
            font_headings_family=llm_output.get("font_headings_family", ""),
            voice_tone=llm_output.get("voice_tone", ""),
            keywords=llm_output.get("keywords", ""),
            description=llm_output.get("description", ""),
            archetype=llm_output.get("archetype", ""),
            target_audience=llm_output.get("target_audience", ""),
        )

        brand_name = llm_output.get("brand_name", "Unknown Brand")
        base_slug = slugify(brand_name)
        slug = base_slug
        logo_url = llm_output.get("logo_url") or scraper_result.get("metadata", {}).get("logo", "")
        counter = 1
        while Brand.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        brand = Brand.objects.create(
            dna=brand_dna,
            name=brand_name,
            slug=slug,
            page_url=state.get("input_url", ""),
            logo_url=logo_url,
            primary_color=llm_output.get("primary_color", ""),
            industry=llm_output.get("industry", ""),
            user_id=state.get("user_id"),
        )

        if not Brand.objects.create:
            if brand.dna:
                brand.dna.delete()
            brand.dna = brand_dna
            brand.name = brand_name
            brand.industry = llm_output.get("industry", "")
            if logo_url:
                brand.logo_url = logo_url
            if state.get("user_id"):
                brand.user_id = state.get("user_id")
            brand.save()

        return {
            "brand_id": str(brand.uuid),
            "db_saved": True,
        }
    except Exception as e:
        return {"error": f"Persistence error: {str(e)}"}
