from ...state import ContentPipelineState
from ....utils.gemini_utils import call_gemini, extract_text, parse_json
from .prompt import build_prompt


def research_platform_node(state: ContentPipelineState) -> dict:
    prompt = build_prompt(
        state.get("topic", "general content"),
        state.get("platform", "Instagram"),
    )
    raw = call_gemini(prompt)
    text = extract_text(raw)
    return {"research_platform": parse_json(text)}
