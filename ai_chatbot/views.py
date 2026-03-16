"""
AI Chatbot API Views.

This module provides REST API endpoints for the MARK AI chatbot system.
"""

import time
import json
import logging
import concurrent.futures
from django.conf import settings
from django.utils import timezone
from django.http import StreamingHttpResponse
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from django.db.models import Q

from .models import ChatConversation, ChatMessage, ChatMemory, ChatSuggestion
from .serializers import (
    ChatConversationListSerializer,
    ChatConversationDetailSerializer,
    ChatConversationCreateSerializer,
    ChatMessageSerializer,
    SendMessageRequestSerializer,
    SendMessageResponseSerializer,
    ChatMemorySerializer,
    ChatSuggestionSerializer,
)
from .graphs.orchestrator import process_message_sync, process_message_stream
from brand_dna_extractor.models import Brand

logger = logging.getLogger(__name__)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _get_permission_classes():
    """Return permission classes based on DEV_MODE setting."""
    dev_mode = getattr(settings, 'DEV_MODE_ALLOW_UNAUTHENTICATED', False)
    if isinstance(dev_mode, str):
        dev_mode = dev_mode.lower() in ('true', '1', 'yes')
    return [AllowAny] if dev_mode else [IsAuthenticated]


def _get_user_info(request):
    """Extract user info from request, with DEV_MODE fallback."""
    if request.user and request.user.is_authenticated:
        return {
            'user_id': getattr(request.user, 'user_id', None),
            'tenant_id': getattr(request.user, 'tenant_id', None),
            'email': getattr(request.user, 'email', None),
        }
    
    dev_mode = getattr(settings, 'DEV_MODE_ALLOW_UNAUTHENTICATED', False)
    if isinstance(dev_mode, str):
        dev_mode = dev_mode.lower() in ('true', '1', 'yes')
    if dev_mode:
        data = request.data if hasattr(request, 'data') else {}
        params = request.query_params if hasattr(request, 'query_params') else {}
        return {
            'user_id': data.get('user_id') or params.get('user_id') or 'dev-user',
            'tenant_id': 'dev-tenant',
            'email': 'dev@mark.ai',
        }
    return None


def _format_brand_context(brand) -> dict:
    """
    Format a Brand ORM object (with optional related BrandDNA) into a
    flat dict suitable for injection into agent context.
    """
    dna = getattr(brand, 'dna', None)
    return {
        "name": brand.name,
        "industry": getattr(brand, 'industry', '') or '',
        "page_url": getattr(brand, 'page_url', '') or '',
        "primary_color": getattr(dna, 'primary_color', '') or '' if dna else '',
        "secondary_color": getattr(dna, 'secondary_color', '') or '' if dna else '',
        "accent_color": getattr(dna, 'accent_color', '') or '' if dna else '',
        "voice_tone": getattr(dna, 'voice_tone', '') or '' if dna else '',
        "keywords": getattr(dna, 'keywords', '') or '' if dna else '',
        "description": getattr(dna, 'description', '') or '' if dna else '',
        "archetype": getattr(dna, 'archetype', '') or '' if dna else '',
        "target_audience": getattr(dna, 'target_audience', '') or '' if dna else '',
    }


def _load_brand_data(brand_uuid: str) -> dict | None:
    """Load Brand + BrandDNA from DB and return formatted dict, or None on failure."""
    if not brand_uuid:
        return None
    try:
        brand = Brand.objects.select_related('dna').filter(uuid=brand_uuid).first()
        if brand:
            return _format_brand_context(brand)
    except Exception as exc:
        logger.warning("Could not load brand data for %s: %s", brand_uuid, exc)
    return None


def _fire_memory_extraction(messages, user_id, brand_id, tenant_id):
    """Fire-and-forget memory extraction in a background thread."""
    try:
        from .graphs.memory_manager import extract_and_save_memories
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(extract_and_save_memories, messages, user_id, brand_id, tenant_id)
    except Exception as exc:
        logger.debug("Memory extraction skipped: %s", exc)


# ============================================================================
# CONVERSATION VIEWS
# ============================================================================

@extend_schema(tags=['Chatbot'])
class ChatConversationListView(generics.ListCreateAPIView):
    """List all chat conversations for the current user or create a new one."""
    serializer_class = ChatConversationListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user_info = _get_user_info(self.request)
        user_id = user_info.get('user_id') if user_info else None
        queryset = ChatConversation.objects.filter(user_id=user_id).order_by('-updated_at')
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        conv_type = self.request.query_params.get('type')
        if conv_type:
            queryset = queryset.filter(conversation_type=conv_type)
        return queryset

    def perform_create(self, serializer):
        user_info = _get_user_info(self.request)
        user_id = user_info.get('user_id') if user_info else None
        tenant_id = user_info.get('tenant_id') if user_info else None
        serializer.save(user_id=user_id, tenant_id=tenant_id)


@extend_schema(tags=['Chatbot'])
class ChatConversationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete a specific chat conversation."""
    serializer_class = ChatConversationDetailSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'uuid'

    def get_queryset(self):
        user_info = _get_user_info(self.request)
        user_id = user_info.get('user_id') if user_info else None
        return ChatConversation.objects.filter(user_id=user_id)


@extend_schema(tags=['Chatbot'])
class ChatMessageListView(generics.ListAPIView):
    """List messages for a specific conversation."""
    serializer_class = ChatMessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        conversation_uuid = self.kwargs.get('conversation_uuid')
        user_info = _get_user_info(self.request)
        user_id = user_info.get('user_id') if user_info else None
        conversation = ChatConversation.objects.filter(
            uuid=conversation_uuid, user_id=user_id
        ).first()
        if not conversation:
            return ChatMessage.objects.none()
        return ChatMessage.objects.filter(conversation=conversation).order_by('created_at')


# ============================================================================
# SEND MESSAGE
# ============================================================================

@extend_schema(
    summary="Send a message to MARK AI",
    description="""
    Send a message to the MARK AI chatbot and receive a response.

    The AI will:
    - Route your message to the appropriate specialized agent
    - Auto-inject brand DNA when brand_uuid is provided
    - Load long-term memories about the user
    - Query the database for your brand data when relevant
    - Search the web for current information when needed
    - Provide professional, strategic marketing guidance
    """,
    request=SendMessageRequestSerializer,
    responses={200: SendMessageResponseSerializer},
    tags=['Chatbot']
)
class ChatSendMessageView(APIView):
    """Send a message to the MARK AI chatbot (batch response)."""
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        return [p() for p in _get_permission_classes()]

    def post(self, request):
        serializer = SendMessageRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"success": False, "error": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user_info = _get_user_info(request)
        user_id = user_info.get('user_id') if user_info else None
        tenant_id = user_info.get('tenant_id') if user_info else None

        message = serializer.validated_data.get('message')
        conversation_uuid = serializer.validated_data.get('conversation_uuid')
        brand_uuid = serializer.validated_data.get('brand_uuid')

        # Get or create conversation
        conversation = None
        if conversation_uuid:
            conversation = ChatConversation.objects.filter(
                uuid=conversation_uuid, user_id=user_id
            ).first()

        if not conversation:
            conversation = ChatConversation.objects.create(
                user_id=user_id,
                tenant_id=tenant_id,
                brand_id=brand_uuid,
                title=message[:80] + "…" if len(message) > 80 else message,
                conversation_type='general',
            )
            conversation_uuid = conversation.uuid

        # Load conversation history (last 20 messages)
        all_msgs = list(
            conversation.messages.values('role', 'content').order_by('created_at')
        )
        conversation_history = all_msgs[-20:] if len(all_msgs) > 20 else all_msgs

        # Determine effective brand_id
        effective_brand_id = brand_uuid or (
            str(conversation.brand_id) if conversation.brand_id else None
        )

        # Auto-load brand DNA from DB
        brand_data = _load_brand_data(effective_brand_id)

        # Load long-term memories for this user
        memory_context = ""
        try:
            from .graphs.memory_manager import load_memories
            memory_context = load_memories(user_id, effective_brand_id)
        except Exception as exc:
            logger.debug("Memory load skipped: %s", exc)

        # Process through MARK multi-agent system
        start_ts = time.monotonic()
        try:
            result = process_message_sync(
                message=message,
                user_id=user_id,
                tenant_id=tenant_id,
                brand_id=effective_brand_id,
                conversation_history=conversation_history,
                conversation_type=conversation.conversation_type,
                brand_data=brand_data,
                memory_context=memory_context,
            )
        except Exception as e:
            logger.exception("MARK agent error for user %s", user_id)
            result = {
                "success": False,
                "response": "I encountered an error processing your request. Please try again.",
                "agent_used": "error",
                "agent_sequence": [],
                "tool_executions": 0,
                "error": str(e),
            }
        elapsed_ms = int((time.monotonic() - start_ts) * 1000)

        # Persist messages
        response_content = (result.get("response") or "").strip()
        if not response_content:
            response_content = "I apologize, but I couldn't generate a response. Please try again."
            result["success"] = False

        ChatMessage.objects.create(
            conversation=conversation,
            role='user',
            message_type='text',
            content=message,
        )
        assistant_msg = ChatMessage.objects.create(
            conversation=conversation,
            role='assistant',
            message_type='text',
            content=response_content,
            agent_name=result.get("agent_used", "unknown"),
            processing_time_ms=elapsed_ms,
        )
        conversation.update_last_message_time()

        # Fire memory extraction in background (non-blocking)
        if result.get("success") and user_id:
            from langchain_core.messages import HumanMessage, AIMessage
            recent_msgs = [HumanMessage(content=message), AIMessage(content=response_content)]
            _fire_memory_extraction(recent_msgs, user_id, effective_brand_id, tenant_id)

        return Response(
            {
                "success": result.get("success", True),
                "response": response_content,
                "conversation_uuid": conversation_uuid,
                "message_uuid": assistant_msg.uuid,
                "agent_used": result.get("agent_used", "unknown"),
                "agent_sequence": result.get("agent_sequence", []),
                "processing_time_ms": elapsed_ms,
                "error": result.get("error"),
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=['Chatbot'])
class ChatStreamMessageView(APIView):
    """
    Stream a MARK AI response using Server-Sent Events (SSE).

    SSE event types:
      { "type": "token",  "content": "..." }   — partial text token
      { "type": "done",   "agent": "...", "message_uuid": "..." }  — stream complete
      { "type": "error",  "message": "..." }   — error
    """
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        return [p() for p in _get_permission_classes()]

    def post(self, request, conversation_uuid):
        user_info = _get_user_info(request)
        if not user_info or not user_info.get('user_id'):
            return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

        user_id = user_info.get('user_id')
        tenant_id = user_info.get('tenant_id')

        message = request.data.get('message', '').strip()
        if not message:
            return Response({"error": "message is required"}, status=status.HTTP_400_BAD_REQUEST)

        brand_uuid = request.data.get('brand_uuid')

        # Get or create conversation
        conversation = ChatConversation.objects.filter(
            uuid=conversation_uuid, user_id=user_id
        ).first()

        if not conversation:
            conversation = ChatConversation.objects.create(
                user_id=user_id,
                tenant_id=tenant_id,
                brand_id=brand_uuid,
                title=message[:80] + "…" if len(message) > 80 else message,
                conversation_type='general',
            )

        # Load history
        all_msgs = list(
            conversation.messages.values('role', 'content').order_by('created_at')
        )
        conversation_history = all_msgs[-20:] if len(all_msgs) > 20 else all_msgs

        effective_brand_id = brand_uuid or (
            str(conversation.brand_id) if conversation.brand_id else None
        )

        brand_data = _load_brand_data(effective_brand_id)

        memory_context = ""
        try:
            from .graphs.memory_manager import load_memories
            memory_context = load_memories(user_id, effective_brand_id)
        except Exception as exc:
            logger.debug("Memory load skipped: %s", exc)

        def event_stream():
            full_response_parts = []
            agent_used = "unknown"

            try:
                for event in process_message_stream(
                    message=message,
                    user_id=user_id,
                    tenant_id=tenant_id,
                    brand_id=effective_brand_id,
                    conversation_history=conversation_history,
                    conversation_type=conversation.conversation_type,
                    brand_data=brand_data,
                    memory_context=memory_context,
                ):
                    if event.get("type") == "token":
                        full_response_parts.append(event["content"])
                        yield f'data: {json.dumps(event)}\n\n'
                    elif event.get("type") == "done":
                        agent_used = event.get("agent", "unknown")
                    elif event.get("type") == "error":
                        yield f'data: {json.dumps(event)}\n\n'
                        return

            except Exception as exc:
                logger.exception("SSE stream error for user %s", user_id)
                yield f'data: {json.dumps({"type": "error", "message": str(exc)})}\n\n'
                return

            # Persist to DB after streaming completes
            full_response = "".join(full_response_parts).strip()
            if not full_response:
                full_response = "I processed your request but couldn't generate a response."

            ChatMessage.objects.create(
                conversation=conversation,
                role='user',
                message_type='text',
                content=message,
            )
            asst_msg = ChatMessage.objects.create(
                conversation=conversation,
                role='assistant',
                message_type='text',
                content=full_response,
                agent_name=agent_used,
            )
            conversation.update_last_message_time()

            # Fire memory extraction (non-blocking)
            if user_id:
                from langchain_core.messages import HumanMessage, AIMessage
                recent = [HumanMessage(content=message), AIMessage(content=full_response)]
                _fire_memory_extraction(recent, user_id, effective_brand_id, tenant_id)

            yield f'data: {json.dumps({"type": "done", "agent": agent_used, "message_uuid": str(asst_msg.uuid), "conversation_uuid": str(conversation.uuid)})}\n\n'

        response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
        response['X-Accel-Buffering'] = 'no'
        response['Cache-Control'] = 'no-cache'
        return response


@extend_schema(tags=['Chatbot'])
class ChatGenerateImageView(APIView):
    """
    Generate a marketing image using DALL-E 3.
    """
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        return [p() for p in _get_permission_classes()]

    def post(self, request):
        prompt = request.data.get('prompt', '').strip()
        if not prompt:
            return Response({"error": "prompt is required"}, status=status.HTTP_400_BAD_REQUEST)

        brand_uuid = request.data.get('brand_uuid')
        size = request.data.get('size', '1024x1024')
        quality = request.data.get('quality', 'standard')

        # Build brand-aware optimized prompt
        brand_data = _load_brand_data(brand_uuid)
        final_prompt = _build_image_prompt(prompt, brand_data)

        try:
            from .graphs.tools import ImageGenerationTool
            tool = ImageGenerationTool()
            result = tool._run(prompt=final_prompt, size=size, quality=quality)

            if not result.get("success"):
                return Response(
                    {"success": False, "error": result.get("error", "Image generation failed")},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            return Response(
                {
                    "success": True,
                    "image_url": result["url"],
                    "revised_prompt": result.get("revised_prompt", final_prompt),
                    "original_prompt": prompt,
                    "size": result.get("size", size),
                    "quality": result.get("quality", quality),
                },
                status=status.HTTP_200_OK,
            )

        except Exception as exc:
            logger.exception("Image generation error")
            return Response(
                {"success": False, "error": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


def _build_image_prompt(user_prompt: str, brand_data: dict | None) -> str:
    """Inject brand identity into a DALL-E 3 prompt."""
    if not brand_data or not brand_data.get("name"):
        return user_prompt

    try:
        from openai import OpenAI
        import os
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

        system = (
            "You are an expert AI image prompt engineer specializing in branded marketing visuals. "
            "Given a user's image idea and brand identity, rewrite it as a rich DALL-E 3 prompt "
            "that incorporates the brand's color palette, visual style, and voice."
        )
        user_msg = (
            f"User's image idea: {user_prompt}\n\n"
            f"Brand: {brand_data.get('name')}\n"
            f"Primary color: {brand_data.get('primary_color', '')}\n"
            "Rewrite as a detailed DALL-E 3 prompt:"
        )
        resp = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user_msg}],
            temperature=0.6,
        )
        return resp.choices[0].message.content.strip() or user_prompt
    except Exception:
        return user_prompt


@extend_schema(tags=['Chatbot'])
class ChatSuggestionsView(APIView):
    """Get suggested questions/prompts for the chat interface."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        conversation_type = request.query_params.get('type', 'general')
        suggestions = ChatSuggestion.objects.filter(
            is_active=True
        ).filter(
            Q(required_conversation_type='') |
            Q(required_conversation_type=conversation_type)
        ).order_by('category', 'display_order')[:10]
        serializer = ChatSuggestionSerializer(suggestions, many=True)
        return Response(serializer.data)


@extend_schema(tags=['Chatbot'])
class ChatMemoryListView(generics.ListAPIView):
    """List memories extracted from chat conversations."""
    serializer_class = ChatMemorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user_info = _get_user_info(self.request)
        user_id = user_info.get('user_id') if user_info else None
        queryset = ChatMemory.objects.filter(user_id=user_id, is_active=True).order_by('-updated_at')
        memory_type = self.request.query_params.get('type')
        if memory_type:
            queryset = queryset.filter(memory_type=memory_type)
        brand_uuid = self.request.query_params.get('brand')
        if brand_uuid:
            queryset = queryset.filter(brand_id=brand_uuid)
        return queryset


@extend_schema(tags=['Chatbot'])
class ChatQuickActionView(APIView):
    """Quick actions for common chat operations."""
    permission_classes = [IsAuthenticated]

    def post(self, request, action):
        user_info = _get_user_info(request)
        user_id = user_info.get('user_id') if user_info else None

        if action == 'summarize':
            conversation_uuid = request.data.get('conversation_uuid')
            conversation = ChatConversation.objects.filter(
                uuid=conversation_uuid, user_id=user_id
            ).first()
            if not conversation:
                return Response({"error": "Conversation not found"}, status=status.HTTP_404_NOT_FOUND)

            summary = f"Conversation with {conversation.messages.count()} messages."
            conversation.context_summary = summary
            conversation.save()
            return Response({"summary": summary})

        elif action == 'clear':
            conversation_uuid = request.data.get('conversation_uuid')
            conversation = ChatConversation.objects.filter(
                uuid=conversation_uuid, user_id=user_id
            ).first()
            if conversation:
                conversation.messages.all().delete()
                return Response({"success": True, "message": "Conversation cleared"})
            return Response({"error": "Conversation not found"}, status=status.HTTP_404_NOT_FOUND)

        return Response({"error": "Unknown action"}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Full Content Generation Pipeline",
    description="""
    Run a high-fidelity marketing content generation pipeline.
    This mirrors the MARK R&D n8n workflow exactly:
    1. Parallel research (trends, competitors, platform specs)
    2. Strategic rationale + primary copy + variations (Cialdini-powered)
    3. Visual prompt engineering (image description)
    4. Optional DALL-E 3 image generation
    """,
    request=OpenApiTypes.OBJECT,  # Could be more specific if desired
    tags=['Chatbot']
)
class ContentPipelineView(APIView):
    """
    Direct access to the sequential content generation pipeline.
    """
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        return [p() for p in _get_permission_classes()]

    def post(self, request):
        post_idea = request.data.get('post_idea', '').strip()
        platform = request.data.get('platform', 'instagram').lower()
        
        if not post_idea:
            return Response(
                {"success": False, "error": "post_idea is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        brand_uuid = request.data.get('brand_uuid')
        brand_data = _load_brand_data(brand_uuid)

        # Build pipeline request dict
        pipeline_data = {
            "post_idea": post_idea,
            "platform": platform,
            "tone": request.data.get('tone', 'professional'),
            "brand_name": brand_data.get("name", "") if brand_data else request.data.get('brand_name', ''),
            "brand_dna": brand_data if brand_data else {},
            "target_audience": request.data.get('target_audience', '') or (
                brand_data.get('target_audience', '') if brand_data else ''
            ),
            "industry": request.data.get('industry', '') or (
                brand_data.get('industry', '') if brand_data else ''
            ),
            "additional_context": request.data.get('additional_context', ''),
            "generate_image": bool(request.data.get('generate_image', False)),
        }

        try:
            from .graphs.content_pipeline import generate_from_dict
            result = generate_from_dict(pipeline_data)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as exc:
            logger.exception("Content pipeline error")
            return Response(
                {"success": False, "error": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
