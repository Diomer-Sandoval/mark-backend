from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from creation_studio.graphs.create_carousel.state import CarouselPipelineState
from .prompt import SYSTEM_PROMPT, build_user_prompt

MODEL = "gpt-4.1-mini"
llm = ChatOpenAI(model=MODEL)


def carousel_strategist_node(state: CarouselPipelineState) -> dict:
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=build_user_prompt(state)),
    ]
    response = llm.invoke(messages)

    from creation_studio.graphs.utils.gemini_utils import parse_json

    strategy = parse_json(response.content)
    return {
        "carousel_strategy": strategy,
        "caption": strategy.get("caption", ""),
        "hashtags": strategy.get("hashtags", []),
    }
