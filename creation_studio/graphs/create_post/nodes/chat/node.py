from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage

from ...state import AgentState
from .prompt import SYSTEM_PROMPT
from .tools import tools

MODEL = "gpt-4.1-mini"

llm = ChatOpenAI(model=MODEL)
if tools:
    llm = llm.bind_tools(tools)


def chat_node(state: AgentState):
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = llm.invoke(messages)
    return {"messages": [response]}
