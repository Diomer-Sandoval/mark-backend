from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from ...state import BrandDNAState
from .prompt import SYSTEM_PROMPT
from .tools import tools

MODEL = "gpt-4.1-mini"

llm = ChatOpenAI(model=MODEL)
if tools:
    llm = llm.bind_tools(tools)


def extractor_node(state: BrandDNAState):
    brand_input = state.get("brand_input", "")
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Extract the brand DNA from the following information:\n\n{brand_input}"),
    ] + state["messages"]
    response = llm.invoke(messages)
    return {"messages": [response]}
