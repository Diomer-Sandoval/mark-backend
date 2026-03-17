"""
MARK Multi-Agent Orchestrator.

This module builds and compiles the LangGraph that orchestrates
all specialized agents from the MARK 2.0 architecture.
"""

from typing import Literal, Callable, Generator
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage

from .state import MARKAgentState, create_initial_state
from .agents import (
    router_agent,
    onboarding_agent,
    market_analysis_agent,
    trends_agent,
    platform_agent,
    strategy_agent,
    content_agent,
    review_agent,
    database_agent,
    general_agent,
    image_generation_agent,
    learning_agent,
    get_all_tools,
)


def should_continue(state: MARKAgentState) -> Literal["tools", "pipeline_router", "respond"]:
    """Determine if we should call tools, advance the pipeline, or respond."""
    messages = state.get("messages", [])

    if not messages:
        return "respond"

    last_message = messages[-1]

    # Check if the last message has tool calls
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"

    # Check if we're in pipeline mode and there are more steps
    if state.get("pipeline_mode"):
        steps = state.get("pipeline_steps", [])
        idx = state.get("pipeline_current_index", 0)
        if idx + 1 < len(steps):
            return "pipeline_router"

    return "respond"


def route_to_agent(state: MARKAgentState) -> str:
    """Route to the appropriate agent based on current state."""
    current_agent = state.get("current_agent", "general")
    # Normalize "image" → "image_generation" for graph node names
    if current_agent == "image":
        return "image_generation"
    return current_agent


def pipeline_router_node(state: MARKAgentState) -> MARKAgentState:
    """Advance the pipeline to the next step."""
    if not state.get("pipeline_mode"):
        return state
    steps = state.get("pipeline_steps", [])
    idx = state.get("pipeline_current_index", 0) + 1
    state["pipeline_current_index"] = idx
    if idx < len(steps):
        state["current_agent"] = steps[idx]
    return state


def route_after_pipeline(state: MARKAgentState) -> str:
    """Route from pipeline_router to the next agent or END."""
    if not state.get("pipeline_mode"):
        return END
    steps = state.get("pipeline_steps", [])
    idx = state.get("pipeline_current_index", 0)
    if idx < len(steps):
        next_agent = steps[idx]
        if next_agent == "image":
            return "image_generation"
        return next_agent
    return END


def agent_node_wrapper(agent_func: Callable) -> Callable:
    """Wrap an agent function to handle execution."""
    def wrapper(state: MARKAgentState) -> MARKAgentState:
        try:
            return agent_func(state)
        except Exception as e:
            state["error"] = str(e)
            state["final_response"] = "I encountered an error processing your request. Let me try a different approach."
            return state
    return wrapper


def build_mark_agent():
    """
    Build the complete MARK multi-agent graph.

    Graph structure:
    1. START → router
    2. router → [specialized_agent]
    3. specialized_agent → tools (if tool calls) → specialized_agent
    4. specialized_agent → pipeline_router (if pipeline has more steps) → next_agent
    5. specialized_agent → END (when complete)
    """
    graph = StateGraph(MARKAgentState)

    # Add all agent nodes
    graph.add_node("router", agent_node_wrapper(router_agent))
    graph.add_node("onboarding", agent_node_wrapper(onboarding_agent))
    graph.add_node("market_analysis", agent_node_wrapper(market_analysis_agent))
    graph.add_node("trends", agent_node_wrapper(trends_agent))
    graph.add_node("platform", agent_node_wrapper(platform_agent))
    graph.add_node("strategy", agent_node_wrapper(strategy_agent))
    graph.add_node("content", agent_node_wrapper(content_agent))
    graph.add_node("review", agent_node_wrapper(review_agent))
    graph.add_node("database", agent_node_wrapper(database_agent))
    graph.add_node("general", agent_node_wrapper(general_agent))
    graph.add_node("image_generation", agent_node_wrapper(image_generation_agent))
    graph.add_node("learning", agent_node_wrapper(learning_agent))
    graph.add_node("pipeline_router", pipeline_router_node)

    # Add tool node
    tools = get_all_tools()
    tool_node = ToolNode(tools)
    graph.add_node("tools", tool_node)

    # START → router
    graph.add_edge(START, "router")

    # Router → appropriate agent
    graph.add_conditional_edges(
        "router",
        route_to_agent,
        {
            "onboarding": "onboarding",
            "market_analysis": "market_analysis",
            "trends": "trends",
            "platform": "platform",
            "strategy": "strategy",
            "content": "content",
            "review": "review",
            "database": "database",
            "general": "general",
            "image_generation": "image_generation",
            "learning": "learning",
            "router": "general",  # Fallback
        },
    )

    # All agents can call tools, advance pipeline, or end
    all_agent_nodes = [
        "onboarding", "market_analysis", "trends", "platform",
        "strategy", "content", "review", "database", "general",
        "image_generation", "learning",
    ]
    for agent_name in all_agent_nodes:
        graph.add_conditional_edges(
            agent_name,
            should_continue,
            {
                "tools": "tools",
                "pipeline_router": "pipeline_router",
                "respond": END,
            },
        )

    # Tools → back to the calling agent
    graph.add_conditional_edges(
        "tools",
        route_to_agent,
        {
            "onboarding": "onboarding",
            "market_analysis": "market_analysis",
            "trends": "trends",
            "platform": "platform",
            "strategy": "strategy",
            "content": "content",
            "review": "review",
            "database": "database",
            "general": "general",
            "image_generation": "image_generation",
            "learning": "learning",
            "router": "general",
        },
    )

    # Pipeline router → next agent or END
    graph.add_conditional_edges(
        "pipeline_router",
        route_after_pipeline,
        {
            "onboarding": "onboarding",
            "market_analysis": "market_analysis",
            "trends": "trends",
            "platform": "platform",
            "strategy": "strategy",
            "content": "content",
            "review": "review",
            "database": "database",
            "general": "general",
            "image_generation": "image_generation",
            "learning": "learning",
            END: END,
        },
    )

    return graph.compile(checkpointer=None)


# Singleton instance
_mark_agent = None


def get_mark_agent():
    """Get or create the MARK agent singleton."""
    global _mark_agent
    if _mark_agent is None:
        _mark_agent = build_mark_agent()
    return _mark_agent


def reset_mark_agent():
    """Force rebuild the agent (call after code changes)."""
    global _mark_agent
    _mark_agent = None


def extract_final_response(state: MARKAgentState) -> MARKAgentState:
    """Extract the final response from the last AI message if not set."""
    if state.get("final_response"):
        return state

    messages = state.get("messages", [])
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.content:
            state["final_response"] = msg.content
            return state

    state["final_response"] = "I processed your request but couldn't generate a proper response. Please try again."
    return state


def _build_state_from_params(
    message: str,
    user_id: str,
    tenant_id: str,
    brand_id: str,
    conversation_history: list,
    conversation_type: str,
    brand_data: dict,
    memory_context: str,
) -> MARKAgentState:
    """Shared helper: build initial MARKAgentState from call parameters."""
    state = create_initial_state(
        user_id=user_id,
        tenant_id=tenant_id,
        brand_id=brand_id,
        conversation_type=conversation_type,
    )

    if brand_data:
        state["context"]["brand_data"] = brand_data
    if memory_context:
        state["context"]["memory_context"] = memory_context

    messages = []
    if conversation_history:
        for msg in conversation_history:
            if msg.get("role") == "user":
                messages.append(HumanMessage(content=msg.get("content", "")))
            elif msg.get("role") == "assistant":
                messages.append(AIMessage(content=msg.get("content", "")))
    messages.append(HumanMessage(content=message))
    state["messages"] = messages

    return state


def process_message_sync(
    message: str,
    user_id: str = None,
    tenant_id: str = None,
    brand_id: str = None,
    conversation_history: list = None,
    conversation_type: str = "general",
    brand_data: dict = None,
    memory_context: str = "",
) -> dict:
    """Synchronous: process a user message through the MARK agent system."""
    state = _build_state_from_params(
        message, user_id, tenant_id, brand_id,
        conversation_history, conversation_type, brand_data, memory_context,
    )

    agent = get_mark_agent()

    try:
        result = agent.invoke(state, config={"recursion_limit": 10})
        result = extract_final_response(result)

        return {
            "success": True,
            "response": result.get("final_response", "No response generated"),
            "agent_used": result.get("current_agent", "unknown"),
            "agent_sequence": result.get("agent_sequence", []),
            "tool_executions": len(result.get("tool_executions", [])),
            "error": result.get("error"),
        }
    except Exception as e:
        import traceback
        return {
            "success": False,
            "response": "I apologize, but I encountered an error processing your request. Please try again.",
            "error": str(e),
            "traceback": traceback.format_exc(),
            "agent_used": "error",
            "agent_sequence": [],
            "tool_executions": 0,
        }


def process_message_stream(
    message: str,
    user_id: str = None,
    tenant_id: str = None,
    brand_id: str = None,
    conversation_history: list = None,
    conversation_type: str = "general",
    brand_data: dict = None,
    memory_context: str = "",
) -> Generator[dict, None, None]:
    """
    Generator: stream tokens from the MARK agent system via LangGraph message streaming.

    Yields dicts:
      {"type": "token",  "content": "<text chunk>"}
      {"type": "done",   "agent": "<agent_name>", "agent_sequence": [...]}
      {"type": "error",  "message": "<error text>"}
    """
    state = _build_state_from_params(
        message, user_id, tenant_id, brand_id,
        conversation_history, conversation_type, brand_data, memory_context,
    )

    agent = get_mark_agent()
    final_agent = "unknown"
    agent_sequence = []

    try:
        for chunk, metadata in agent.stream(state, stream_mode="messages", config={"recursion_limit": 10}):
            node = metadata.get("langgraph_node", "")
            if node and node not in ("tools", "router", "pipeline_router"):
                final_agent = node
                if not agent_sequence or agent_sequence[-1] != node:
                    agent_sequence.append(node)

            # Only yield text tokens from actual agent nodes — skip router/pipeline JSON
            if (
                node not in ("router", "pipeline_router")
                and isinstance(chunk, (AIMessage, AIMessageChunk))
                and isinstance(chunk.content, str)
                and chunk.content
            ):
                yield {"type": "token", "content": chunk.content}

        yield {"type": "done", "agent": final_agent, "agent_sequence": agent_sequence}

    except Exception as e:
        import traceback
        yield {"type": "error", "message": str(e), "traceback": traceback.format_exc()}


async def process_message(
    message: str,
    user_id: str = None,
    tenant_id: str = None,
    brand_id: str = None,
    conversation_history: list = None,
    conversation_type: str = "general",
    brand_data: dict = None,
    memory_context: str = "",
) -> dict:
    """
    Async wrapper: process a user message through the MARK agent system.
    """
    import asyncio
    from functools import partial

    loop = asyncio.get_event_loop()
    func = partial(
        process_message_sync,
        message,
        user_id,
        tenant_id,
        brand_id,
        conversation_history,
        conversation_type,
        brand_data,
        memory_context,
    )
    return await loop.run_in_executor(None, func)
