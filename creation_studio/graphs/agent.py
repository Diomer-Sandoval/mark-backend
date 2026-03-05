from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition

from .state import AgentState
from .nodes.chat import chat_node
from .nodes.chat.tools import tools


def build_agent():
    graph = StateGraph(AgentState)

    graph.add_node("chat", chat_node)

    if tools:
        graph.add_node("tools", ToolNode(tools))
        graph.add_edge(START, "chat")
        graph.add_conditional_edges("chat", tools_condition)
        graph.add_edge("tools", "chat")
    else:
        graph.add_edge(START, "chat")
        graph.add_edge("chat", END)

    return graph.compile()
