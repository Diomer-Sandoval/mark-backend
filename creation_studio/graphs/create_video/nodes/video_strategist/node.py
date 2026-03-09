import json

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from creation_studio.graphs.utils.gemini_utils import parse_json
from .prompt import SYSTEM_PROMPT, build_user_prompt

MODEL = "gpt-4.1-mini"
llm = ChatOpenAI(model=MODEL)


def video_strategist_node(state: dict) -> dict:
    # Combine research into a compact object for prompt builder
    combined_research = {
        "trends": {
            "top_hooks": state.get("research_trends", {}).get("top_hooks", [])[:3],
            "visual_trends": state.get("research_trends", {}).get("visual_trends", {}),
            "top_pick": state.get("research_trends", {}).get("top_pick", ""),
        },
        "competitors": {
            "gaps_and_opportunities": state.get("research_competitors", {}).get("gaps_and_opportunities", [])[:4],
            "differentiation_angles": state.get("research_competitors", {}).get("differentiation_angles", [])[:3],
        },
        "platform": {
            "hook_timing": state.get("research_platform", {}).get("hook_timing", {}),
            "format_constraints": state.get("research_platform", {}).get("format_constraints", {}),
            "hashtag_strategy": state.get("research_platform", {}).get("hashtag_strategy", {}),
        },
    }

    augmented_state = {**state, "_research_combined": combined_research}

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=build_user_prompt(augmented_state)),
    ]
    response = llm.invoke(messages)
    strategy = parse_json(response.content)

    return {
        "video_strategy": strategy,
        "caption": strategy.get("caption", ""),
        "hashtags": strategy.get("hashtags", []),
    }
