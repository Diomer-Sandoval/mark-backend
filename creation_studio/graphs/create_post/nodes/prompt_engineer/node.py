from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from ...state import ContentPipelineState
from .prompt import SYSTEM_PROMPT, build_user_prompt

MODEL = "gpt-4.1-mini"
llm = ChatOpenAI(model=MODEL)


def prompt_engineer_node(state: ContentPipelineState) -> dict:
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=build_user_prompt(state)),
    ]
    response = llm.invoke(messages)
    return {"image_prompt": response.content}
