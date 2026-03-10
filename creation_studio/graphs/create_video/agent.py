from langgraph.graph import StateGraph, START, END

from .state import VideoPipelineState
from creation_studio.graphs.shared.nodes.research_trends import research_trends_node
from creation_studio.graphs.shared.nodes.research_competitors import research_competitors_node
from creation_studio.graphs.shared.nodes.research_platform import research_platform_node
from .nodes.video_strategist import video_strategist_node
from .nodes.template_retriever import template_retriever_node
from .nodes.generate_scenes import generate_scenes_node


def build_video_agent():
    graph = StateGraph(VideoPipelineState)

    graph.add_node("research_trends", research_trends_node)
    graph.add_node("research_competitors", research_competitors_node)
    graph.add_node("research_platform", research_platform_node)
    graph.add_node("video_strategist", video_strategist_node)
    graph.add_node("template_retriever", template_retriever_node)
    graph.add_node("generate_scenes", generate_scenes_node)

    # Fan-out: all 3 research agents start simultaneously
    graph.add_edge(START, "research_trends")
    graph.add_edge(START, "research_competitors")
    graph.add_edge(START, "research_platform")

    # Fan-in: strategist waits for all 3
    graph.add_edge("research_trends", "video_strategist")
    graph.add_edge("research_competitors", "video_strategist")
    graph.add_edge("research_platform", "video_strategist")

    graph.add_edge("video_strategist", "template_retriever")
    graph.add_edge("template_retriever", "generate_scenes")
    graph.add_edge("generate_scenes", END)

    return graph.compile()
