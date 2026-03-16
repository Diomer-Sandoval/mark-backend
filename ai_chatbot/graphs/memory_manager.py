"""
Memory Manager for MARK AI Chatbot.

Handles loading long-term memories to inject into agent context and
extracting new memories from completed conversation turns.
"""

import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


def load_memories(user_id: str, brand_id: Optional[str] = None) -> str:
    """
    Load a user's stored memories from the database and return them
    as a formatted context string ready to be injected into agent prompts.

    Returns an empty string if no memories exist or on any error.
    """
    if not user_id:
        return ""

    try:
        from ai_chatbot.models import ChatMemory
        from django.utils import timezone

        qs = ChatMemory.objects.filter(
            user_id=user_id,
            is_active=True,
        ).order_by('-updated_at')

        if brand_id:
            qs = qs.filter(brand__uuid=brand_id)

        memories = list(qs[:20])
        if not memories:
            return ""

        # Update access tracking in bulk
        pks = [m.pk for m in memories]
        ChatMemory.objects.filter(pk__in=pks).update(
            access_count=models_access_count_increment(pks),
            last_accessed_at=timezone.now(),
        )

        lines = ["MEMORY CONTEXT (facts remembered from previous conversations with this user):"]
        for m in memories:
            lines.append(f"  [{m.memory_type}] {m.key}: {m.value}")

        return "\n".join(lines)

    except Exception as exc:
        logger.debug("Memory load error for user %s: %s", user_id, exc)
        return ""


def models_access_count_increment(pks):
    """Helper returning an F() expression for incrementing access_count."""
    from django.db.models import F
    # We return a fixed expression; the actual update uses F() in the queryset
    return F('access_count') + 1


def extract_and_save_memories(
    messages: list,
    user_id: str,
    brand_id: Optional[str],
    tenant_id: Optional[str],
) -> None:
    """
    Use gpt-4.1-mini to extract memorable facts from the last few messages
    and save them to the ChatMemory table.

    This function is designed to run in a background thread (fire-and-forget).
    All exceptions are caught and logged — it must never crash the main thread.
    """
    if not user_id or not messages:
        return

    try:
        from openai import OpenAI

        # Build a compact conversation text from the last 4 messages
        recent = messages[-4:] if len(messages) >= 4 else messages
        conversation_lines = []
        for m in recent:
            if hasattr(m, 'type'):
                role = m.type  # HumanMessage → "human", AIMessage → "ai"
            elif hasattr(m, 'role'):
                role = m.role
            else:
                role = "message"
            content = getattr(m, 'content', str(m))
            if content:
                conversation_lines.append(f"{role}: {content[:500]}")

        if not conversation_lines:
            return

        conversation_text = "\n".join(conversation_lines)

        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        resp = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You extract memorable facts from marketing conversations to personalize future interactions.\n\n"
                        "Return a JSON object with a 'memories' key containing an array of facts.\n"
                        "Each fact: {\"memory_type\": \"preference|business_fact|goal|constraint|insight|feedback\", "
                        "\"key\": \"short_snake_case_key\", \"value\": \"concise fact\", \"confidence\": 0.0-1.0}\n\n"
                        "Rules:\n"
                        "- Only extract DEFINITIVE facts, not speculation\n"
                        "- Minimum confidence 0.7 to be worth storing\n"
                        "- Return {\"memories\": []} if nothing notable\n"
                        "- Keys should be short and reusable (e.g. 'preferred_platform', 'monthly_budget', 'target_audience')\n"
                        "- Values should be concise (max 200 chars)"
                    ),
                },
                {
                    "role": "user",
                    "content": f"Extract memorable facts from:\n\n{conversation_text}",
                },
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
        )

        raw = resp.choices[0].message.content or "{}"
        data = json.loads(raw)
        memory_items = data.get("memories", [])

        if not memory_items:
            return

        from ai_chatbot.models import ChatMemory

        brand_obj = None
        if brand_id:
            try:
                from brand_dna_extractor.models import Brand
                brand_obj = Brand.objects.filter(uuid=brand_id).first()
            except Exception:
                pass

        saved_count = 0
        for item in memory_items:
            confidence = float(item.get("confidence", 0))
            if confidence < 0.6:
                continue

            key = str(item.get("key", "")).strip()[:200]
            value = str(item.get("value", "")).strip()[:500]
            memory_type = item.get("memory_type", "insight")

            if not key or not value:
                continue

            valid_types = {"preference", "business_fact", "brand_attribute", "goal", "constraint", "insight", "feedback"}
            if memory_type not in valid_types:
                memory_type = "insight"

            try:
                ChatMemory.objects.update_or_create(
                    user_id=user_id,
                    brand=brand_obj,
                    key=key,
                    defaults={
                        "memory_type": memory_type,
                        "value": value,
                        "confidence_score": confidence,
                        "is_active": True,
                    },
                )
                saved_count += 1
            except Exception as exc:
                logger.debug("Could not save memory '%s': %s", key, exc)

        if saved_count:
            logger.debug("Saved %d memories for user %s", saved_count, user_id)

    except Exception as exc:
        logger.debug("Memory extraction error for user %s: %s", user_id, exc)
