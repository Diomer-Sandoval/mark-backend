from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition

from .state import BrandDNAState
from .nodes.extractor.node import extractor_node
from .nodes.extractor.tools import tools
from .nodes.formatter.node import formatter_node


def build_agent():
    graph = StateGraph(BrandDNAState)

    graph.add_node("extractor", extractor_node)
    graph.add_node("formatter", formatter_node)

    if tools:
        graph.add_node("tools", ToolNode(tools))
        graph.add_edge(START, "extractor")
        graph.add_conditional_edges("extractor", tools_condition, {"tools": "tools", "__end__": "formatter"})
        graph.add_edge("tools", "extractor")
    else:
        graph.add_edge(START, "extractor")
        graph.add_edge("extractor", "formatter")

    graph.add_edge("formatter", END)

    return graph.compile()
