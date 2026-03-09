from creation_studio.graphs.utils.gemini_utils import call_gemini, extract_text, parse_json
from .prompt import build_prompt


def research_competitors_node(state: dict) -> dict:
    identity = state.get("identity", {})
    platforms = state.get("platforms", ["instagram"])
    prompt = build_prompt(
        identity.get("name", "Unknown"),
        state.get("prompt", "general content"),
        ", ".join(platforms),
    )
    raw = call_gemini(prompt)
    text = extract_text(raw)
    return {"research_competitors": parse_json(text)}
