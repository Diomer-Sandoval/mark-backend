from langgraph.graph import StateGraph, START, END

from .state import BrandDNAState
from .nodes.scraper.node import scraper_node
from .nodes.preprocessing.node import preprocessing_node
from .nodes.ai_agent.node import ai_agent_node
from .nodes.persistence.node import persistence_node


def build_brand_dna_graph():
    graph = StateGraph(BrandDNAState)

    graph.add_node("Scraper", scraper_node)
    graph.add_node("Preprocessing", preprocessing_node)
    graph.add_node("AIAgent", ai_agent_node)
    graph.add_node("Persistence", persistence_node)

    graph.add_edge(START, "Scraper")
    graph.add_conditional_edges("Scraper", lambda s: END if s.get("error") else "Preprocessing")
    graph.add_conditional_edges("Preprocessing", lambda s: END if s.get("error") else "AIAgent")
    graph.add_conditional_edges("AIAgent", lambda s: END if s.get("error") else "Persistence")
    graph.add_edge("Persistence", END)

    return graph.compile()
