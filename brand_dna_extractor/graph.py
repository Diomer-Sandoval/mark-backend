import json
from typing import TypedDict, Optional, Dict, Any
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

# We import the utility from the same package
from .utils import BrandScraperUtility


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


# Node 1: Scraper
def scraper_node(state: BrandDNAState):
    url = state["input_url"]
    result = BrandScraperUtility.scrape_url(url)
    
    if not result.get("success"):
        return {"scraper_result": result, "error": result.get("error")}
        
    return {"scraper_result": result, "error": None}


# Node 2: Preprocessing
def preprocessing_node(state: BrandDNAState):
    if state.get("error"):
        return state
        
    result = state["scraper_result"]
    metadata = result.get("metadata", {})
    colors = result.get("extracted_colors", [])
    fonts = result.get("extracted_fonts", [])
    clean_text = result.get("clean_text", "")
    
    # Structure for LLM
    structured_data = {
        "title": metadata.get("title", ""),
        "description": metadata.get("description", ""),
        "logo_url": metadata.get("logo", ""),
        "extracted_hex_colors": colors,
        "extracted_font_families": fonts,
        "raw_text_snippet": clean_text
    }
    
    preprocessed_json = json.dumps(structured_data, indent=2)
    return {"preprocessed_data": preprocessed_json}


# Define the expected JSON output
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


# Node 3: AI Agent
def ai_agent_node(state: BrandDNAState):
    if state.get("error"):
        return state
        
    preprocessed_data = state["preprocessed_data"]
    
    # Instantiate the LLM (OpenAI)
    llm = ChatOpenAI(model="gpt-4o", temperature=0.2)
    parser = JsonOutputParser(pydantic_object=BrandDNAOutput)
    
    system_prompt = """You are an expert Brand DNA Architect.
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

Output exactly valid JSON matching the schema format.
"""
    
    user_prompt = "Here is the extracted website data:\n{data}\n\n{format_instructions}"
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", user_prompt)
    ])
    
    chain = prompt | llm | parser
    
    try:
        response = chain.invoke({
            "data": preprocessed_data,
            "format_instructions": parser.get_format_instructions()
        })
        return {"llm_output": response}
    except Exception as e:
        return {"error": f"LLM parsing error: {str(e)}"}


# Node 4: Persistence
def persistence_node(state: BrandDNAState):
    if state.get("error"):
        return state
        
    llm_output = state["llm_output"]
    input_url = state["input_url"]
    scraper_result = state["scraper_result"]
    logo_url = scraper_result.get("metadata", {}).get("logo", "")
    
    # LLM extracts the clean name, fallback to full scraped title if it fails
    title = llm_output.get("brand_name") or scraper_result.get("metadata", {}).get("title", "Unknown Brand")
    
    # We do imports here to avoid django initialization issues during module load
    from creation_studio.models import Brand, BrandDNA
    from django.utils.text import slugify
    import uuid
    
    try:
        # Create BrandDNA record
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
            raw_data=scraper_result
        )
        
        # Determine a slug
        base_slug = slugify(title)
        if not base_slug:
            base_slug = "brand"
        slug = base_slug
        counter = 1
        while Brand.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
            
        # Create or update Brand record
        brand, created = Brand.objects.get_or_create(
            page_url=input_url,
            defaults={
                "name": title,
                "slug": slug,
                "logo_url": logo_url,
                "dna": dna_record,
                "industry": llm_output.get("industry", ""),
                "user_id": state.get("user_id"),
                "tenant_id": state.get("tenant_id")
            }
        )
        
        # Update existing brand's DNA if it already existed
        if not created:
            if brand.dna:
                brand.dna.delete() # cleanup old dna
            brand.dna = dna_record
            brand.name = title  # Update the clean name since the website title could change
            brand.industry = llm_output.get("industry", "") # Update industry
            
            if logo_url and not brand.logo_url:
                brand.logo_url = logo_url
                
            # Always forcefully update user and tenant if they were passed
            if state.get("user_id"):
                brand.user_id = state.get("user_id")
            if state.get("tenant_id"):
                brand.tenant_id = state.get("tenant_id")
                
            brand.save()
            
        return {"db_saved": True, "brand_id": str(brand.uuid)}
        
    except Exception as e:
        return {"error": f"Database error: {str(e)}", "db_saved": False}


# Build Graph
def build_brand_dna_graph():
    graph = StateGraph(BrandDNAState)
    
    # Add nodes
    graph.add_node("Scraper", scraper_node)
    graph.add_node("Preprocessing", preprocessing_node)
    graph.add_node("AIAgent", ai_agent_node)
    graph.add_node("Persistence", persistence_node)
    
    # Add edges
    graph.add_edge(START, "Scraper")
    
    def next_after_scraper(state: BrandDNAState):
        return END if state.get("error") else "Preprocessing"
        
    def next_after_preprocessing(state: BrandDNAState):
        return END if state.get("error") else "AIAgent"
        
    def next_after_ai(state: BrandDNAState):
        return END if state.get("error") else "Persistence"
        
    graph.add_conditional_edges("Scraper", next_after_scraper)
    graph.add_conditional_edges("Preprocessing", next_after_preprocessing)
    graph.add_conditional_edges("AIAgent", next_after_ai)
    graph.add_edge("Persistence", END)
    
    return graph.compile()
