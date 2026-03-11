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
    voice_tone: str = Field(description="Brand voice tone describing how the brand communicates (e.g. 'Playful but professional', 'Serious and authoritative')")
    archetype: str = Field(description="Classic brand archetype (e.g., 'The Hero', 'The Creator', 'The Rebel', 'The Sage', 'The Innocent', 'The Everyman', 'The Lover', 'The Magician', 'The Ruler', 'The Jester', 'The Caregiver', 'The Explorer')")
    target_audience: str = Field(description="Concise description of the primary target audience (who they are, what they value, what problem is solved)")
    keywords: str = Field(description="Comma-separated brand keywords")
    description: str = Field(description="Brand description and positioning statement - what makes them unique")


SYSTEM_PROMPT = """You are an expert Brand DNA Architect.
Your task is to analyze extracted raw data from a brand's website and output a structured JSON describing their Brand DNA.
You MUST:
1. Extract a clean, concise brand name.
2. Classify the brand's primary industry.
3. Map extracted colors to Material Design 3 roles.
4. Suggest prominent font families for headings and body.
5. Define the brand 'voice_tone' and its primary 'archetype' (e.g. 'The Hero', 'The Explorer').
6. Describe the 'target_audience' based on the language and value propositions found.
7. Provide a comma-separated list of keywords.
8. Provide a concise brand description.

Output exactly valid JSON matching the schema format."""

USER_PROMPT = "Here is the extracted website data:\n{data}\n\n{format_instructions}"
