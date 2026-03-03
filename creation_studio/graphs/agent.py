from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition

from .state import AgentState


def build_agent(tools: list = None, model: str = "gpt-4.1-mini"):
    """Build a basic ReAct agent graph.

    Args:
        tools: List of LangChain tools to bind to the agent.
        model: OpenAI model name to use.

    Returns:
        Compiled LangGraph graph.
    """
    tools = tools or []
    llm = ChatOpenAI(model=model)

    if tools:
        llm = llm.bind_tools(tools)

    def call_model(state: AgentState):
        response = llm.invoke(state["messages"])
        return {"messages": [response]}

    graph = StateGraph(AgentState)
    graph.add_node("agent", call_model)

    if tools:
        tool_node = ToolNode(tools)
        graph.add_node("tools", tool_node)
        graph.add_edge(START, "agent")
        graph.add_conditional_edges("agent", tools_condition)
        graph.add_edge("tools", "agent")
    else:
        graph.add_edge(START, "agent")
        graph.add_edge("agent", END)

    return graph.compile()
