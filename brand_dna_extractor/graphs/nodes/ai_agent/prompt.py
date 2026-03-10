from pydantic import BaseModel, Field


class BrandDNAOutput(BaseModel):
    brand_name: str = Field(description="Clean, concise brand name extracted from the website context")
    industry: str = Field(description="Primary industry or vertical the brand operates in (e.g., 'Retail', 'Technology', 'Footwear', 'Consumer Goods')")
    primary_color: str = Field(description="Hex code for primary color (Material Design 3 role)")
    secondary_color: str = Field(description="Hex code for secondary color (Material Design 3 role)")
    accent_color: str = Field(description="Hex code for accent/tertiary color")
    complementary_color: str = Field(description="Hex code for complementary/background color ensuring WCAG 2.1 contrast")
    font_body_family: str = Field(description="Body typography font family")
    font_headings_family: str = Field(description="Headings typography font family")
    voice_tone: str = Field(description="Brand voice tone and archetype classification")
    keywords: str = Field(description="Comma-separated brand keywords")
    description: str = Field(description="Brand description and positioning")


SYSTEM_PROMPT = """You are an expert Brand DNA Architect.
Your task is to analyze extracted raw data from a brand's website and output a structured JSON describing their Brand DNA.
You MUST:
1. Extract a clean, concise brand name (e.g. 'Nike Colombia' rather than 'Nike Colombia | Official Site...').
2. Classify the brand's primary industry (e.g., 'Retail', 'Finance', 'Technology') based on their products/services.
3. Map extracted colors to Material Design 3 roles (Primary, Secondary, Tertiary/Accent, Background/Complementary).
4. Ensure WCAG 2.1 contrast ratios are kept in mind for accessibility.
5. Classify the typography and suggest the most prominent fonts for headings and body.
6. Classify the brand archetype and define a 'voice_tone'.
7. Provide a comma-separated list of keywords representing the brand.
8. Provide a concise target description of the brand.

Output exactly valid JSON matching the schema format."""

USER_PROMPT = "Here is the extracted website data:\n{data}\n\n{format_instructions}"
