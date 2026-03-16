"""
Agent Node Implementations for MARK Multi-Agent System.
"""

import json
from typing import Dict, Any
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
from langchain_openai import ChatOpenAI

from .state import MARKAgentState
from .prompts import (
    ROUTER_SYSTEM_PROMPT,
    ONBOARDING_SYSTEM_PROMPT,
    COMPETITOR_SYSTEM_PROMPT,
    TRENDS_SYSTEM_PROMPT,
    PLATFORM_SYSTEM_PROMPT,
    STRATEGY_SYSTEM_PROMPT,
    CONTENT_SYSTEM_PROMPT,
    REVIEW_SYSTEM_PROMPT,
    LEARNING_SYSTEM_PROMPT,
    GENERAL_SYSTEM_PROMPT,
    DATABASE_SYSTEM_PROMPT,
)
from .tools import get_all_tools, get_database_tools, get_research_tools, ImageGenerationTool


# Model configuration
MODEL = "gpt-4.1-mini"
TEMPERATURE = 0.7


def get_llm(tools=None, temperature: float = TEMPERATURE):
    """Get configured LLM instance."""
    llm = ChatOpenAI(model=MODEL, temperature=temperature)
    if tools:
        llm = llm.bind_tools(tools)
    return llm


def format_conversation_history(messages: list) -> str:
    """Format conversation history for context."""
    formatted = []
    for msg in messages[-10:]:  # Last 10 messages
        role = "User" if isinstance(msg, HumanMessage) else "Assistant"
        content = msg.content[:500] if len(msg.content) > 500 else msg.content
        formatted.append(f"{role}: {content}")
    return "\n".join(formatted)


def get_context_info(state: MARKAgentState) -> str:
    """Extract and format context information including brand DNA and memory."""
    context = state.get("context", {})
    parts = []

    if context.get("brand_id"):
        parts.append(f"Brand ID: {context['brand_id']}")
    if context.get("user_id"):
        parts.append(f"User ID: {context['user_id']}")
    if context.get("conversation_type"):
        parts.append(f"Conversation Type: {context['conversation_type']}")
    if context.get("extracted_goals"):
        parts.append(f"Goals: {', '.join(context['extracted_goals'])}")

    # Inject brand DNA if available (auto-loaded from DB by the view layer)
    brand_data = context.get("brand_data")
    if brand_data and brand_data.get("name"):
        parts.append("---")
        parts.append(f"Brand: {brand_data['name']} | Industry: {brand_data.get('industry', '')}")
        if brand_data.get("voice_tone"):
            parts.append(f"Voice/Tone: {brand_data['voice_tone']} | Archetype: {brand_data.get('archetype', '')}")
        primary = brand_data.get("primary_color", "")
        secondary = brand_data.get("secondary_color", "")
        accent = brand_data.get("accent_color", "")
        if any([primary, secondary, accent]):
            parts.append(f"Brand Colors: Primary={primary} Secondary={secondary} Accent={accent}")
        if brand_data.get("target_audience"):
            parts.append(f"Target Audience: {brand_data['target_audience']}")
        if brand_data.get("keywords"):
            parts.append(f"Brand Keywords: {brand_data['keywords']}")
        if brand_data.get("description"):
            parts.append(f"Brand Description: {brand_data['description'][:300]}")
        parts.append("---")

    # Inject long-term memory context if available
    memory_context = context.get("memory_context")
    if memory_context:
        parts.append(memory_context)

    return "\n".join(parts) if parts else "No specific context available."


# ============================================================================
# ROUTER AGENT
# ============================================================================

def router_agent(state: MARKAgentState) -> MARKAgentState:
    """
    Router agent - classifies user intent with pure LLM classification.
    Uses a single fast LLM call with structured JSON output for reliable routing.
    """
    messages = state.get("messages", [])
    if not messages:
        return state

    last_message = messages[-1]
    if not isinstance(last_message, HumanMessage):
        return state

    # Build a brief conversation history snippet for context
    history_snippet = ""
    for msg in messages[-6:-1]:  # Up to last 5 prior messages
        role = "User" if isinstance(msg, HumanMessage) else "Assistant"
        history_snippet += f"{role}: {msg.content[:200]}\n"

    context = state.get("context", {})
    brand_id = context.get("brand_id")
    user_id = context.get("user_id")

    classification_prompt = f"""You are the MARK AI Router. Classify the user's intent into exactly ONE category.

Available categories and when to use them:
- database     : user asks about THEIR OWN data ("how many posts", "show me my brands", "my analytics", "what have I posted", "my performance")
- onboarding   : user wants to set up / describe their business, brand values, target audience, or goals
- market_analysis : competitor analysis, market research, industry landscape
- trends       : what is trending now, popular content formats, industry trends
- platform     : platform specs, image dimensions, best time to post, algorithm tips for specific platforms
- strategy     : marketing strategy, content strategy, campaign planning, Cialdini persuasion
- content      : CREATE new posts/captions/copy/content ("write me", "create a post", "draft", "generate", "help me write")
- review       : review or critique existing content the user provides
- general      : greetings, general marketing questions, anything that doesn't fit above

User context:
- Has brand: {"yes (brand_id=" + str(brand_id) + ")" if brand_id else "no"}
- User ID: {user_id or "unknown"}

Conversation history:
{history_snippet or "(start of conversation)"}

User's latest message: "{last_message.content}"

Respond with ONLY a single JSON object, no markdown, no explanation:
{{"intent": "<category_name>", "confidence": <0.0-1.0>, "reasoning": "<one sentence>"}}"""

    try:
        llm = get_llm(temperature=0.0)  # Zero temperature for deterministic routing
        response = llm.invoke([SystemMessage(content=classification_prompt)])
        raw = response.content.strip()

        # Parse JSON response
        import json
        # Handle markdown code blocks if LLM wraps the JSON
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        classification = json.loads(raw.strip())
        agent_name = classification.get("intent", "general").lower().strip()

        valid_agents = [
            "onboarding", "market_analysis", "trends", "platform",
            "strategy", "content", "review", "database", "general",
            "image", "learning",
        ]
        if agent_name not in valid_agents:
            agent_name = "general"

    except Exception:
        # Fallback: simple keyword safety net
        msg_lower = last_message.content.lower()
        if any(k in msg_lower for k in ['how many', 'my posts', 'my brands', 'my analytics', 'show me my']):
            agent_name = "database"
        elif any(k in msg_lower for k in ['generate image', 'create image', 'create a visual', 'visual for', 'picture of', 'dalle']):
            agent_name = "image"
        elif any(k in msg_lower for k in ['create', 'write', 'draft', 'generate', 'caption']):
            agent_name = "content"
        else:
            agent_name = "general"

    # ── Pipeline mode detection ───────────────────────────────────────────────
    # For high-intent content/strategy requests, chain multiple agents automatically.
    PIPELINE_INTENTS = {
        "content": ["trends", "platform", "strategy", "content", "review"],
        "strategy": ["trends", "market_analysis", "strategy"],
    }
    msg_lower_check = last_message.content.lower() if isinstance(last_message, HumanMessage) else ""
    # Only activate pipeline for clear multi-step requests (longer, specific queries)
    is_deep_request = len(msg_lower_check.split()) > 8 and any(
        k in msg_lower_check for k in ["create a post", "write a post", "create content", "marketing strategy", "content strategy", "campaign"]
    )
    if agent_name in PIPELINE_INTENTS and is_deep_request:
        steps = PIPELINE_INTENTS[agent_name]
        state["pipeline_mode"] = True
        state["pipeline_steps"] = steps
        state["pipeline_current_index"] = 0
        state["current_agent"] = steps[0]
        state["agent_sequence"] = state.get("agent_sequence", []) + ["router"] + steps
    else:
        state["pipeline_mode"] = False
        state["pipeline_steps"] = []
        state["pipeline_current_index"] = 0
        state["current_agent"] = agent_name
        state["agent_sequence"] = state.get("agent_sequence", []) + ["router", agent_name]

    return state


# ============================================================================
# ONBOARDING AGENT
# ============================================================================

def onboarding_agent(state: MARKAgentState) -> MARKAgentState:
    """
    Onboarding & Context Agent - understands business and brand.
    """
    messages = state.get("messages", [])
    if not messages:
        return state
    
    context_info = get_context_info(state)
    history = format_conversation_history(messages)
    
    prompt = f"""{ONBOARDING_SYSTEM_PROMPT}

## Current Context:
{context_info}

## Conversation History:
{history}

Your task: Deeply understand the user's business and help them define clear Business → Marketing → Content mapping.
Ask strategic questions if needed. Present the mapping clearly for validation.
"""
    
    llm = get_llm()
    response = llm.invoke([SystemMessage(content=prompt)])
    
    # Store output
    state["onboarding_output"] = {
        "response": response.content,
        "extracted_info": {},  # Would be populated by parsing
    }
    
    # Add response to messages
    state["messages"] = messages + [AIMessage(content=response.content, name="onboarding")]
    state["final_response"] = response.content
    
    return state


# ============================================================================
# DATABASE AGENT
# ============================================================================

def database_agent(state: MARKAgentState) -> MARKAgentState:
    """
    Database Query Agent - retrieves user's data.
    """
    messages = state.get("messages", [])
    if not messages:
        return state
    
    last_message = messages[-1]
    
    # Check if this is a tool result (ToolMessage) - if so, we need to generate final response
    from langchain_core.messages import ToolMessage
    is_tool_result = isinstance(last_message, ToolMessage)
    
    # Get context
    context = state.get("context", {})
    user_id = context.get("user_id")
    brand_id = context.get("brand_id")
    
    context_info = get_context_info(state)
    history = format_conversation_history(messages[:-1])
    
    # If no brand_id in context but we have user_id, try to get user's first brand
    if not brand_id and user_id:
        try:
            from brand_dna_extractor.models import Brand
            user_brand = Brand.objects.filter(user_id=user_id).first()
            if user_brand:
                brand_id = user_brand.uuid
                context["brand_id"] = brand_id
                context["brand_name"] = user_brand.name
        except Exception:
            pass
    
    # Get database tools
    tools = get_database_tools()
    
    # If this is a tool result, generate final response based on tool output
    if is_tool_result:
        prompt = f"""You are the MARK Database Query Agent. 

The tools have been executed and returned data. Based on the tool results in the conversation history, provide a helpful response to the user's original question.

## User's Original Question:
Look at the conversation history to find the user's question.

## Tool Results:
{last_message.content}

## Instructions:
1. Summarize the data in a clear, helpful way
2. Answer the user's specific question directly
3. Provide insights based on the data
4. If the data shows errors or no results, explain why

Respond conversationally without referencing "tools" or "data" explicitly.
"""
    else:
        # First call - need to use tools
        prompt = f"""{DATABASE_SYSTEM_PROMPT}

## User Information:
- User ID: {user_id or "Not available"}
- Brand ID: {brand_id or "Not available - ask user to select a brand"}
- Brand Name: {context.get("brand_name", "Unknown")}

## Current Context:
{context_info}

## Conversation History:
{history}

## User's Question:
{last_message.content if isinstance(last_message, HumanMessage) else ""}

## Instructions:
1. If Brand ID is available, use the tools to query the data
2. If no Brand ID, use get_user_brands tool to show user's brands
3. Always provide specific numbers and insights from the database
4. If asking about "posts", use get_posts tool
5. If asking about "brands", use get_user_brands tool
6. If asking about "analytics" or "performance", use get_analytics or get_best_performing_content tools
7. Always respond with actual data, not generic explanations
"""
    
    try:
        llm = get_llm(tools=tools if not is_tool_result else None)
        response = llm.invoke([SystemMessage(content=prompt)])
        
        # Check if response contains tool calls
        if hasattr(response, 'tool_calls') and response.tool_calls:
            state["messages"] = messages + [response]
            return state
        
        state["final_response"] = response.content
        state["messages"] = messages + [AIMessage(content=response.content, name="database")]
    except Exception as e:
        # Provide helpful error message
        state["final_response"] = f"I apologize, but I couldn't retrieve your data at the moment. Please ensure you're logged in and have created a brand."
        state["messages"] = messages + [AIMessage(content=state["final_response"], name="database")]
        state["error"] = str(e)
    
    return state


# ============================================================================
# MARKET ANALYSIS AGENT
# ============================================================================

def market_analysis_agent(state: MARKAgentState) -> MARKAgentState:
    """
    Competitor & Market Agent - analyzes competition.
    """
    messages = state.get("messages", [])
    if not messages:
        return state
    
    context_info = get_context_info(state)
    brand_context = state.get("context", {}).get("business_context", {})
    industry = brand_context.get("industry", "Unknown")
    
    # Get research tools
    tools = get_research_tools()
    
    prompt = f"""{COMPETITOR_SYSTEM_PROMPT}

## Current Context:
{context_info}
Industry: {industry}

## User's Request:
{messages[-1].content if messages else ""}

Research competitors and provide a differentiation framework. Identify:
1. Key competitors in the space
2. Their content patterns (what they do)
3. Saturated themes to avoid
4. Differentiation opportunities
5. "Do Not Duplicate" list
"""
    
    llm = get_llm(tools=tools)
    response = llm.invoke([SystemMessage(content=prompt)])
    
    state["market_analysis_output"] = {"response": response.content}
    state["final_response"] = response.content
    state["messages"] = messages + [AIMessage(content=response.content, name="market_analysis")]
    
    return state


# ============================================================================
# TRENDS AGENT
# ============================================================================

def trends_agent(state: MARKAgentState) -> MARKAgentState:
    """
    Trends Agent - identifies current trends.
    """
    messages = state.get("messages", [])
    if not messages:
        return state
    
    context_info = get_context_info(state)
    brand_context = state.get("context", {}).get("business_context", {})
    industry = brand_context.get("industry", "marketing")
    
    tools = get_research_tools()
    
    prompt = f"""{TRENDS_SYSTEM_PROMPT}

## Current Context:
{context_info}
Industry: {industry}

## User's Request:
{messages[-1].content if messages else ""}

Research current trends and provide:
1. Hot trends (act now)
2. Rising opportunities
3. Stable performers
4. Declining (avoid)
5. Strategic recommendations

Focus on trends relevant to the industry and brand positioning.
"""
    
    llm = get_llm(tools=tools)
    response = llm.invoke([SystemMessage(content=prompt)])
    
    state["trends_output"] = {"response": response.content}
    state["final_response"] = response.content
    state["messages"] = messages + [AIMessage(content=response.content, name="trends")]
    
    return state


# ============================================================================
# PLATFORM AGENT
# ============================================================================

def platform_agent(state: MARKAgentState) -> MARKAgentState:
    """
    Platform Intelligence Agent - provides platform specs.
    """
    messages = state.get("messages", [])
    if not messages:
        return state
    
    prompt = f"""{PLATFORM_SYSTEM_PROMPT}

## User's Question:
{messages[-1].content if messages else ""}

Provide detailed platform specifications including:
- Format options and specs
- Safe zones and restricted areas
- Copy constraints
- Best practices
"""
    
    llm = get_llm()
    response = llm.invoke([SystemMessage(content=prompt)])
    
    state["platform_output"] = {"response": response.content}
    state["final_response"] = response.content
    state["messages"] = messages + [AIMessage(content=response.content, name="platform")]
    
    return state


# ============================================================================
# STRATEGY AGENT
# ============================================================================

def strategy_agent(state: MARKAgentState) -> MARKAgentState:
    """
    Strategy Agent - creates marketing strategy with Cialdini principles.
    """
    messages = state.get("messages", [])
    if not messages:
        return state
    
    context_info = get_context_info(state)
    
    # Include outputs from other agents if available
    market_output = state.get("market_analysis_output", {})
    trends_output = state.get("trends_output", {})
    
    prompt = f"""{STRATEGY_SYSTEM_PROMPT}

## Current Context:
{context_info}

## Previous Intelligence:
Market Analysis: {market_output.get('response', 'Not available')[:500] if market_output else 'Not available'}

Trends: {trends_output.get('response', 'Not available')[:500] if trends_output else 'Not available'}

## User's Request:
{messages[-1].content if messages else ""}

Create a strategic framework including:
1. Audience maturity assessment
2. Content pillars with behavioral outcomes
3. Persuasion principles (Cialdini) for each pillar
4. Success metrics
5. Platform-specific considerations

Make clear decisions, not brainstorms. Every recommendation must support business goals.
"""
    
    llm = get_llm()
    response = llm.invoke([SystemMessage(content=prompt)])
    
    state["strategy_output"] = {"response": response.content}
    state["final_response"] = response.content
    state["messages"] = messages + [AIMessage(content=response.content, name="strategy")]
    
    return state


# ============================================================================
# CONTENT AGENT
# ============================================================================

def content_agent(state: MARKAgentState) -> MARKAgentState:
    """
    Content Creation Agent - generates marketing content.
    """
    messages = state.get("messages", [])
    if not messages:
        return state
    
    context_info = get_context_info(state)
    strategy_output = state.get("strategy_output", {})
    brand_id = state.get("context", {}).get("brand_id")
    
    # Get tools for content creation
    tools = []
    if brand_id:
        from .tools import GetBrandInfoTool, SearchTemplatesTool
        tools = [GetBrandInfoTool(), SearchTemplatesTool()]
    
    prompt = f"""{CONTENT_SYSTEM_PROMPT}

## Current Context:
{context_info}

## Strategy Context:
{strategy_output.get('response', 'No strategy defined yet')[:800] if strategy_output else 'No strategy defined yet'}

## User's Request:
{messages[-1].content if messages else ""}

Create content that:
1. Follows the strategic framework
2. Matches brand voice and DNA
3. Respects platform constraints
4. Includes 2+ copy options
5. Provides visual direction
6. Suggests hashtags

Brand ID for reference: {brand_id or 'Not specified'}
"""
    
    llm = get_llm(tools=tools if tools else None)
    response = llm.invoke([SystemMessage(content=prompt)])
    
    state["content_output"] = {"response": response.content}
    state["final_response"] = response.content
    state["messages"] = messages + [AIMessage(content=response.content, name="content")]
    
    return state


# ============================================================================
# REVIEW AGENT
# ============================================================================

def review_agent(state: MARKAgentState) -> MARKAgentState:
    """
    Content Review Agent - evaluates content quality.
    """
    messages = state.get("messages", [])
    if not messages:
        return state
    
    context_info = get_context_info(state)
    strategy_output = state.get("strategy_output", {})
    
    prompt = f"""{REVIEW_SYSTEM_PROMPT}

## Current Context:
{context_info}

## Strategy Framework:
{strategy_output.get('response', 'No strategy defined')[:500] if strategy_output else 'No strategy defined'}

## Content to Review:
{messages[-1].content if messages else ""}

Evaluate the content on:
1. Strategic alignment (25%)
2. Brand fit (25%)
3. Platform compliance (20%)
4. Differentiation (15%)
5. Persuasion effectiveness (15%)

Provide specific scores, feedback, and required changes.
"""
    
    llm = get_llm()
    response = llm.invoke([SystemMessage(content=prompt)])
    
    state["review_output"] = {"response": response.content}
    state["final_response"] = response.content
    state["messages"] = messages + [AIMessage(content=response.content, name="review")]
    
    return state


# ============================================================================
# IMAGE GENERATION AGENT
# ============================================================================

def _optimize_image_prompt(user_message: str, brand_data: dict, strategy_output: dict) -> str:
    """
    Use gpt-4.1-mini to craft a rich DALL-E 3 prompt from the user's request,
    brand identity, and any strategy context.
    """
    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import SystemMessage as SM, HumanMessage as HM

        brand_block = ""
        if brand_data and brand_data.get("name"):
            brand_block = (
                f"Brand: {brand_data['name']}\n"
                f"Colors: {brand_data.get('primary_color','')} / {brand_data.get('secondary_color','')} / {brand_data.get('accent_color','')}\n"
                f"Voice/Tone: {brand_data.get('voice_tone','')}\n"
                f"Industry: {brand_data.get('industry','')}\n"
                f"Keywords: {brand_data.get('keywords','')}\n"
            )

        strategy_block = ""
        if strategy_output and strategy_output.get("response"):
            strategy_block = f"Strategy context:\n{strategy_output['response'][:400]}\n"

        llm = ChatOpenAI(model=MODEL, temperature=0.6)
        response = llm.invoke([
            SM(content=(
                "You are an expert AI image prompt engineer specializing in branded marketing visuals. "
                "Given a user's request, brand identity, and optional strategy context, write a rich "
                "DALL-E 3 prompt (60-120 words) that will generate a professional marketing image. "
                "Incorporate brand colors and visual identity naturally. "
                "Output ONLY the final prompt — no explanations, no quotes."
            )),
            HM(content=(
                f"User request: {user_message}\n\n"
                f"{brand_block}"
                f"{strategy_block}"
                "Write the DALL-E 3 prompt:"
            )),
        ])
        return response.content.strip() or user_message
    except Exception:
        return user_message


def image_generation_agent(state: MARKAgentState) -> MARKAgentState:
    """
    Image Generation Agent - creates branded marketing visuals via DALL-E 3.
    """
    messages = state.get("messages", [])
    if not messages:
        return state

    # Find the user's original message
    user_message = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            user_message = msg.content
            break

    context = state.get("context", {})
    brand_data = context.get("brand_data") or {}
    strategy_output = state.get("strategy_output") or {}

    # Build an optimized, brand-aware prompt
    optimized_prompt = _optimize_image_prompt(user_message, brand_data, strategy_output)

    # Generate image via DALL-E 3
    tool = ImageGenerationTool()
    result = tool._run(prompt=optimized_prompt)

    if result.get("success"):
        image_url = result["url"]
        revised_prompt = result.get("revised_prompt", optimized_prompt)

        state["image_output"] = {
            "url": image_url,
            "revised_prompt": revised_prompt,
            "original_prompt": user_message,
            "optimized_prompt": optimized_prompt,
            "size": result.get("size", "1024x1024"),
            "quality": result.get("quality", "standard"),
        }

        brand_name = brand_data.get("name", "your brand") if brand_data else "your brand"
        response_text = (
            f"Here's your marketing image for {brand_name}!\n\n"
            f"🖼️ **Generated Image:** {image_url}\n\n"
            f"**Prompt used:** {revised_prompt}\n\n"
            f"*Note: This URL expires in 1 hour. Download/save if you need to keep it.*\n\n"
            f"Would you like me to:\n"
            f"- Generate more variations?\n"
            f"- Adjust the style or colors?\n"
            f"- Create copy/caption to pair with this image?"
        )
    else:
        error_msg = result.get("error", "Unknown error")
        state["image_output"] = {"error": error_msg}
        response_text = (
            f"I wasn't able to generate the image: {error_msg}\n\n"
            "Please try again with a more specific description, or I can help you craft a detailed visual brief."
        )

    state["final_response"] = response_text
    state["messages"] = messages + [AIMessage(content=response_text, name="image_generation")]
    return state


# ============================================================================
# LEARNING AGENT
# ============================================================================

def learning_agent(state: MARKAgentState) -> MARKAgentState:
    """
    Learning & Optimization Agent - analyzes performance patterns to improve future content.
    """
    messages = state.get("messages", [])
    if not messages:
        return state

    context_info = get_context_info(state)
    review_output = state.get("review_output") or {}
    brand_id = state.get("context", {}).get("brand_id")

    # Get analytics tools
    from .tools import GetAnalyticsTool, GetBestPerformingContentTool
    tools = [GetAnalyticsTool(), GetBestPerformingContentTool()]

    review_context = ""
    if review_output.get("response"):
        review_context = f"\n## Content Review Results:\n{review_output['response'][:600]}\n"

    prompt = f"""{LEARNING_SYSTEM_PROMPT}

## Current Context:
{context_info}
{review_context}
## Brand ID for Analytics:
{brand_id or "Not specified — ask user to select a brand for performance data"}

## User's Question:
{messages[-1].content if messages else "Analyze my content performance"}

Analyze available performance data and provide specific, actionable optimization insights.
Focus on patterns, not just individual post metrics.
"""

    llm = get_llm(tools=tools if brand_id else None)
    response = llm.invoke([SystemMessage(content=prompt)])

    # Handle tool calls
    if hasattr(response, 'tool_calls') and response.tool_calls:
        state["messages"] = messages + [response]
        return state

    state["learning_output"] = {"response": response.content}
    state["final_response"] = response.content
    state["messages"] = messages + [AIMessage(content=response.content, name="learning")]
    return state


# ============================================================================
# GENERAL AGENT
# ============================================================================

def general_agent(state: MARKAgentState) -> MARKAgentState:
    """
    General Agent - handles all types of queries with tool support.
    """
    messages = state.get("messages", [])
    if not messages:
        return state
    
    context = state.get("context", {})
    user_id = context.get("user_id")
    brand_id = context.get("brand_id")
    
    # Check if this is a tool result message
    from langchain_core.messages import ToolMessage
    last_message = messages[-1]
    is_tool_result = isinstance(last_message, ToolMessage)
    
    # If no brand_id in context but we have user_id, try to get user's first brand
    if not brand_id and user_id:
        try:
            from brand_dna_extractor.models import Brand
            user_brand = Brand.objects.filter(user_id=user_id).first()
            if user_brand:
                brand_id = user_brand.uuid
                context["brand_id"] = brand_id
                context["brand_name"] = user_brand.name
        except Exception:
            pass
    
    context_info = get_context_info(state)
    history = format_conversation_history(messages[:-1])
    
    # Get all tools for general queries
    tools = get_all_tools()
    
    # Determine query type for better routing
    user_message_content = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            user_message_content = msg.content.lower()
            break
    
    # Check if this is a data query, research query, or general question
    is_data_query = any(kw in user_message_content for kw in [
        'how many', 'what are my', 'show me my', 'my posts', 'my brands',
        'my analytics', 'count my', 'list my', 'total posts', 'my data',
        'do i have', 'posts do i', 'brands do i', 'my best', 'my top'
    ])
    
    is_research_query = any(kw in user_message_content for kw in [
        'trends', 'trending', 'competitors', 'competition', 'research',
        'what\'s popular', 'current trends', 'market analysis', 'best practices'
    ])
    
    if is_tool_result:
        # Tool has been executed, generate response based on results
        prompt = f"""{GENERAL_SYSTEM_PROMPT}

## User Information:
- User ID: {user_id or "Not available"}
- Brand ID: {brand_id or "Not available"}
- Brand Name: {context.get("brand_name", "Unknown")}

## Tool Results:
{last_message.content}

## Instructions:
Based on the tool results above, provide a helpful, professional response to the user.
- Summarize the data clearly
- Answer their specific question directly
- Provide insights based on the data
- If no data found, explain why and suggest next steps
"""
    else:
        # First call - analyze query and use tools if needed
        prompt = f"""{GENERAL_SYSTEM_PROMPT}

## User Information:
- User ID: {user_id or "Not available"}
- Brand ID: {brand_id or "Not available"}
- Brand Name: {context.get("brand_name", "Unknown")}

## Current Context:
{context_info}

## Conversation History:
{history}

## User's Message:
{messages[-1].content if messages else ""}

## Query Analysis:
- Is Data Query: {is_data_query}
- Is Research Query: {is_research_query}

## Instructions:
1. If this is a data query about user's OWN data:
   - You MUST use the appropriate database tool (get_posts, get_user_brands, get_analytics, etc.)
   - NEVER make up numbers or data
   
2. If this is a research query about trends, competitors, or general info:
   - You MUST use web_search, search_trends, or research_competitor tools
   - Provide current, relevant information
   
3. If this is a general marketing question:
   - Answer from your knowledge
   - Be specific and actionable
   
4. Be professional, direct, and helpful
"""
    
    try:
        llm = get_llm(tools=tools if not is_tool_result else None, temperature=0.7)
        response = llm.invoke([SystemMessage(content=prompt)])
        
        # Check if response contains tool calls
        if hasattr(response, 'tool_calls') and response.tool_calls:
            # Return state for tool execution
            state["messages"] = messages + [response]
            return state
        
        # Ensure we have a valid response
        response_content = response.content.strip() if response.content else ""
        if not response_content:
            response_content = "I apologize, but I couldn't generate a response. Please try rephrasing your question."
        
        state["final_response"] = response_content
        state["messages"] = messages + [AIMessage(content=response_content, name="general")]
    except Exception as e:
        # Provide helpful error message
        state["final_response"] = "I apologize, but I encountered an error. Please try again or rephrase your question."
        state["messages"] = messages + [AIMessage(content=state["final_response"], name="general")]
        state["error"] = str(e)
    
    return state


# ============================================================================
# AGENT MAPPING
# ============================================================================

AGENT_MAP = {
    "router": router_agent,
    "onboarding": onboarding_agent,
    "market_analysis": market_analysis_agent,
    "trends": trends_agent,
    "platform": platform_agent,
    "strategy": strategy_agent,
    "content": content_agent,
    "review": review_agent,
    "database": database_agent,
    "general": general_agent,
    "image": image_generation_agent,
    "learning": learning_agent,
}


def get_agent(agent_name: str):
    """Get an agent by name."""
    return AGENT_MAP.get(agent_name, general_agent)
