import json
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage

from ...state import BrandDNAState
from .prompt import SYSTEM_PROMPT

MODEL = "gpt-4.1-mini"

llm = ChatOpenAI(model=MODEL)


def formatter_node(state: BrandDNAState):
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = llm.invoke(messages)

    try:
        brand_dna = json.loads(response.content)
    except json.JSONDecodeError:
        brand_dna = {"raw": response.content}

    return {"messages": [response], "brand_dna": brand_dna}
