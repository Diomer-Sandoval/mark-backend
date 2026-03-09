from langgraph.graph import StateGraph, START, END

from .state import CarouselPipelineState
from creation_studio.graphs.shared.nodes.research_trends import research_trends_node
from creation_studio.graphs.shared.nodes.research_competitors import research_competitors_node
from creation_studio.graphs.shared.nodes.research_platform import research_platform_node
from .nodes.carousel_strategist import carousel_strategist_node
from .nodes.template_retriever import template_retriever_node
from .nodes.generate_slides import generate_slides_node


def build_carousel_agent():
    graph = StateGraph(CarouselPipelineState)

    graph.add_node("research_trends", research_trends_node)
    graph.add_node("research_competitors", research_competitors_node)
    graph.add_node("research_platform", research_platform_node)
    graph.add_node("carousel_strategist", carousel_strategist_node)
    graph.add_node("template_retriever", template_retriever_node)
    graph.add_node("generate_slides", generate_slides_node)

    # Fan-out: all 3 research agents start simultaneously
    graph.add_edge(START, "research_trends")
    graph.add_edge(START, "research_competitors")
    graph.add_edge(START, "research_platform")

    # Fan-in: strategist waits for all 3
    graph.add_edge("research_trends", "carousel_strategist")
    graph.add_edge("research_competitors", "carousel_strategist")
    graph.add_edge("research_platform", "carousel_strategist")

    graph.add_edge("carousel_strategist", "template_retriever")
    graph.add_edge("template_retriever", "generate_slides")
    graph.add_edge("generate_slides", END)

    return graph.compile()
