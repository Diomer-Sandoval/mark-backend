from ...state import BrandDNAState


def persistence_node(state: BrandDNAState):
    if state.get("error"):
        return state

    llm_output = state["llm_output"]
    input_url = state["input_url"]
    scraper_result = state["scraper_result"]
    logo_url = scraper_result.get("metadata", {}).get("logo", "")

    title = llm_output.get("brand_name") or scraper_result.get("metadata", {}).get("title", "Unknown Brand")

    # Initialize Django if apps aren't loaded yet (e.g. when running via LangGraph dev server)
    import django
    from django.apps import apps
    if not apps.ready:
        import os
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
        django.setup()

    from creation_studio.models import Brand, BrandDNA
    from django.utils.text import slugify

    try:
        dna_record = BrandDNA.objects.create(
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

        base_slug = slugify(title) or "brand"
        slug = base_slug
        counter = 1
        while Brand.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        brand, created = Brand.objects.get_or_create(
            page_url=input_url,
            defaults={
                "name": title,
                "slug": slug,
                "logo_url": logo_url,
                "dna": dna_record,
                "industry": llm_output.get("industry", ""),
                "user_id": state.get("user_id"),
                "tenant_id": state.get("tenant_id"),
            },
        )

        if not created:
            if brand.dna:
                brand.dna.delete()
            brand.dna = dna_record
            brand.name = title
            brand.industry = llm_output.get("industry", "")
            if logo_url and not brand.logo_url:
                brand.logo_url = logo_url
            if state.get("user_id"):
                brand.user_id = state.get("user_id")
            if state.get("tenant_id"):
                brand.tenant_id = state.get("tenant_id")
            brand.save()

        return {"db_saved": True, "brand_id": str(brand.uuid)}

    except Exception as e:
        return {"error": f"Database error: {str(e)}", "db_saved": False}
