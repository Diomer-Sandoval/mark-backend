"""
State Management for MARK Multi-Agent System.
"""

from typing import Annotated, Any, Dict, List, Optional, TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class AgentContext(TypedDict, total=False):
    """Context information for the current conversation."""
    user_id: Optional[str]
    tenant_id: Optional[str]
    brand_id: Optional[str]
    brand_data: Optional[Dict[str, Any]]
    conversation_type: str
    session_id: str
    extracted_goals: List[str]
    business_context: Dict[str, Any]
    memory_context: Optional[str]  # Formatted string of remembered facts about the user


class ToolExecution(TypedDict):
    """Record of a tool execution."""
    tool_name: str
    input_params: Dict[str, Any]
    output: Any
    execution_time_ms: int
    success: bool
    error_message: Optional[str]


class MARKAgentState(TypedDict):
    """
    State for the MARK multi-agent system.
    
    This state is passed between agents and contains:
    - messages: Chat history
    - context: User/brand context
    - current_agent: Which agent is currently handling the request
    - agent_outputs: Results from each agent
    - tool_executions: Record of tool calls
    - final_response: The assembled final response
    - metadata: Additional processing metadata
    """
    
    # Core conversation state
    messages: Annotated[List[BaseMessage], add_messages]
    
    # User and conversation context
    context: AgentContext
    
    # Current agent routing
    current_agent: str  # Which agent is currently active
    agent_sequence: List[str]  # Sequence of agents that have processed
    
    # Agent outputs
    onboarding_output: Optional[Dict[str, Any]]
    market_analysis_output: Optional[Dict[str, Any]]
    trends_output: Optional[Dict[str, Any]]
    platform_output: Optional[Dict[str, Any]]
    strategy_output: Optional[Dict[str, Any]]
    content_output: Optional[Dict[str, Any]]
    review_output: Optional[Dict[str, Any]]
    image_output: Optional[Dict[str, Any]]
    learning_output: Optional[Dict[str, Any]]

    # Pipeline chaining support
    pipeline_mode: bool
    pipeline_steps: List[str]
    pipeline_current_index: int
    
    # Tool execution tracking
    tool_executions: List[ToolExecution]
    pending_tool_calls: List[Dict[str, Any]]
    
    # Response assembly
    final_response: Optional[str]
    structured_response: Optional[Dict[str, Any]]
    response_metadata: Dict[str, Any]
    
    # Memory and learning
    extracted_insights: List[Dict[str, Any]]
    memories_to_store: List[Dict[str, Any]]
    
    # Error handling
    error: Optional[str]
    retry_count: int


def create_initial_state(
    user_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    brand_id: Optional[str] = None,
    conversation_type: str = "general"
) -> MARKAgentState:
    """Create an initial state for a new conversation."""
    return {
        "messages": [],
        "context": {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "brand_id": brand_id,
            "conversation_type": conversation_type,
            "extracted_goals": [],
            "business_context": {},
        },
        "current_agent": "router",
        "agent_sequence": [],
        "onboarding_output": None,
        "market_analysis_output": None,
        "trends_output": None,
        "platform_output": None,
        "strategy_output": None,
        "content_output": None,
        "review_output": None,
        "image_output": None,
        "learning_output": None,
        "pipeline_mode": False,
        "pipeline_steps": [],
        "pipeline_current_index": 0,
        "tool_executions": [],
        "pending_tool_calls": [],
        "final_response": None,
        "structured_response": None,
        "response_metadata": {},
        "extracted_insights": [],
        "memories_to_store": [],
        "error": None,
        "retry_count": 0,
    }
