from langgraph.graph import StateGraph, START, END

from .state import ContentPipelineState
from creation_studio.graphs.shared.nodes.research_trends import research_trends_node
from creation_studio.graphs.shared.nodes.research_competitors import research_competitors_node
from creation_studio.graphs.shared.nodes.research_platform import research_platform_node
from .nodes.strategist_copywriter import strategist_copywriter_node
from .nodes.prompt_engineer import prompt_engineer_node
from .nodes.generate_image import generate_image_node


def research_router(state: ContentPipelineState):
    """If we have a current copy and don't want to refresh, skip research nodes."""
    if state.get("current_copy") and not state.get("refresh_research"):
        return "skip_research"
    return "do_research"


def research_orchestrator(state: ContentPipelineState):
    """Pass-through node to trigger parallel research fan-out."""
    return state


def build_agent():
    graph = StateGraph(ContentPipelineState)

    # ── Register the nodes ──────────────────────────────────────
    graph.add_node("research_orchestrator", research_orchestrator)
    graph.add_node("research_trends", research_trends_node)
    graph.add_node("research_competitors", research_competitors_node)
    graph.add_node("research_platform", research_platform_node)
    graph.add_node("strategist_copywriter", strategist_copywriter_node)
    graph.add_node("prompt_engineer", prompt_engineer_node)
    graph.add_node("generate_image", generate_image_node)

    # ── Conditional: decide whether to do research or skip to strategist ──
    graph.add_conditional_edges(
        START,
        research_router,
        {
            "do_research": "research_orchestrator",
            "skip_research": "strategist_copywriter",
        },
    )

    # ── Fan-out: from orchestrator to research nodes ────────────────
    graph.add_edge("research_orchestrator", "research_trends")
    graph.add_edge("research_orchestrator", "research_competitors")
    graph.add_edge("research_orchestrator", "research_platform")

    # ── Fan-in: strategist waits for research (if they were run) ───────
    graph.add_edge("research_trends", "strategist_copywriter")
    graph.add_edge("research_competitors", "strategist_copywriter")
    graph.add_edge("research_platform", "strategist_copywriter")

    # ── Sequential: prompt engineer → image generation ───────────
    graph.add_edge("strategist_copywriter", "prompt_engineer")
    graph.add_edge("prompt_engineer", "generate_image")
    graph.add_edge("generate_image", END)

    return graph.compile()


def build_copy_agent():
    """Same pipeline but stops after strategist_copywriter — no image generated."""
    graph = StateGraph(ContentPipelineState)

    graph.add_node("research_orchestrator", research_orchestrator)
    graph.add_node("research_trends", research_trends_node)
    graph.add_node("research_competitors", research_competitors_node)
    graph.add_node("research_platform", research_platform_node)
    graph.add_node("strategist_copywriter", strategist_copywriter_node)

    # ── Conditional: decide whether to do research or skip to strategist ──
    graph.add_conditional_edges(
        START,
        research_router,
        {
            "do_research": "research_orchestrator",
            "skip_research": "strategist_copywriter",
        },
    )

    # ── Fan-out ──────────────────────────────────────────────────
    graph.add_edge("research_orchestrator", "research_trends")
    graph.add_edge("research_orchestrator", "research_competitors")
    graph.add_edge("research_orchestrator", "research_platform")

    graph.add_edge("research_trends", "strategist_copywriter")
    graph.add_edge("research_competitors", "strategist_copywriter")
    graph.add_edge("research_platform", "strategist_copywriter")

    graph.add_edge("strategist_copywriter", END)

    return graph.compile()
