"""
Serializers for AI Chatbot API.
"""

from rest_framework import serializers
from .models import ChatConversation, ChatMessage, ChatMemory, ChatSuggestion


class ChatMessageSerializer(serializers.ModelSerializer):
    """Serializer for chat messages."""
    
    class Meta:
        model = ChatMessage
        fields = [
            'uuid', 'role', 'message_type', 'content', 'content_structured',
            'tool_name', 'agent_name', 'sources', 'created_at',
        ]
        read_only_fields = ['uuid', 'created_at']


class ChatConversationListSerializer(serializers.ModelSerializer):
    """Serializer for conversation list view."""
    
    message_count = serializers.SerializerMethodField()
    formatted_date = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatConversation
        fields = [
            'uuid', 'title', 'conversation_type', 'status',
            'brand', 'message_count', 'created_at', 'updated_at', 'last_message_at',
            'formatted_date'
        ]
        read_only_fields = ['uuid', 'created_at', 'updated_at', 'last_message_at']
    
    def get_message_count(self, obj):
        return obj.messages.count()
    
    def get_formatted_date(self, obj):
        """Return formatted date for display."""
        from django.utils import timezone
        
        date_to_format = obj.last_message_at or obj.updated_at
        if not date_to_format:
            return None
        
        now = timezone.now()
        diff = now - date_to_format
        
        if diff.days == 0:
            if diff.seconds < 3600:
                minutes = diff.seconds // 60
                return f"{minutes} min ago" if minutes > 0 else "Just now"
            else:
                hours = diff.seconds // 3600
                return f"{hours} hour ago" if hours == 1 else f"{hours} hours ago"
        elif diff.days == 1:
            return "Yesterday"
        elif diff.days < 7:
            return f"{diff.days} days ago"
        else:
            return date_to_format.strftime("%b %d")


class ChatConversationDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed conversation view."""
    
    messages = ChatMessageSerializer(many=True, read_only=True)
    
    class Meta:
        model = ChatConversation
        fields = [
            'uuid', 'title', 'conversation_type', 'status',
            'brand', 'context_summary', 'extracted_goals', 'brand_context',
            'messages', 'created_at', 'updated_at', 'last_message_at',
        ]
        read_only_fields = ['uuid', 'created_at', 'updated_at', 'last_message_at']


class ChatConversationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating conversations."""
    
    class Meta:
        model = ChatConversation
        fields = [
            'title', 'conversation_type', 'brand',
        ]


class SendMessageRequestSerializer(serializers.Serializer):
    """Serializer for sending a message."""
    
    message = serializers.CharField(required=True, max_length=10000)
    conversation_uuid = serializers.CharField(required=False, allow_null=True)
    brand_uuid = serializers.CharField(required=False, allow_null=True)
    conversation_history = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list
    )


class SendMessageResponseSerializer(serializers.Serializer):
    """Serializer for message response."""
    
    success = serializers.BooleanField()
    response = serializers.CharField()
    conversation_uuid = serializers.CharField()
    agent_used = serializers.CharField()
    message_uuid = serializers.CharField(required=False)
    error = serializers.CharField(required=False)


class ChatMemorySerializer(serializers.ModelSerializer):
    """Serializer for chat memories."""
    
    class Meta:
        model = ChatMemory
        fields = [
            'uuid', 'memory_type', 'key', 'value', 'value_structured',
            'confidence_score', 'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['uuid', 'created_at', 'updated_at']


class ChatSuggestionSerializer(serializers.ModelSerializer):
    """Serializer for chat suggestions."""
    
    class Meta:
        model = ChatSuggestion
        fields = [
            'uuid', 'category', 'suggestion_text', 'description',
            'required_conversation_type', 'display_order',
        ]
