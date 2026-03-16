"""
Chat Models for MARK AI Assistant.

This module provides models for:
- Chat conversations and session management
- Message history and memory
- User preferences and context
"""

import uuid
from django.db import models


def generate_chat_uuid():
    """Generate a unique UUID for chat entities."""
    return uuid.uuid4().hex[:17]


class ChatConversation(models.Model):
    """
    Represents a chat conversation session with the MARK AI.
    
    Stores conversation metadata, context, and relationships to messages.
    """
    
    CONVERSATION_TYPE_CHOICES = [
        ('general', 'General Chat'),
        ('onboarding', 'Business Onboarding'),
        ('strategy', 'Strategy Development'),
        ('content', 'Content Creation'),
        ('analytics', 'Performance Analytics'),
        ('competitor', 'Competitor Analysis'),
        ('brand_dna', 'Brand DNA Discussion'),
        ('creation', 'Creation Project'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('archived', 'Archived'),
        ('completed', 'Completed'),
    ]
    
    uuid = models.CharField(
        max_length=17,
        primary_key=True,
        default=generate_chat_uuid,
        editable=False
    )
    
    # User information (from SIA authentication)
    user_id = models.CharField(
        max_length=36,
        null=True,
        blank=True,
        db_index=True,
        help_text="SIA User UUID who owns this conversation"
    )
    
    tenant_id = models.CharField(
        max_length=36,
        null=True,
        blank=True,
        db_index=True,
        help_text="SIA Tenant UUID - organization context"
    )
    
    # Associated brand (optional)
    brand = models.ForeignKey(
        'brand_dna_extractor.Brand',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='conversations',
        db_column='brand_uuid'
    )
    
    # Conversation metadata
    title = models.CharField(max_length=255, default="New Conversation")
    conversation_type = models.CharField(
        max_length=20,
        choices=CONVERSATION_TYPE_CHOICES,
        default='general'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )
    
    # Context and memory
    context_summary = models.TextField(
        blank=True,
        help_text="AI-generated summary of conversation context"
    )
    extracted_goals = models.JSONField(
        default=dict,
        blank=True,
        help_text="Business/marketing goals extracted from conversation"
    )
    brand_context = models.JSONField(
        default=dict,
        blank=True,
        help_text="Brand-specific context for this conversation"
    )
    
    # Session metadata
    session_metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional session data (IP, user agent, etc.)"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_message_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'chat_conversations'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user_id', 'status']),
            models.Index(fields=['brand', 'status']),
            models.Index(fields=['conversation_type']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.uuid})"
    
    def update_last_message_time(self):
        """Update the last message timestamp."""
        from django.utils import timezone
        self.last_message_at = timezone.now()
        self.save(update_fields=['last_message_at', 'updated_at'])


class ChatMessage(models.Model):
    """
    Individual message within a chat conversation.
    
    Supports various message types including text, structured data,
    tool calls, and system messages.
    """
    
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
        ('tool', 'Tool'),
    ]
    
    MESSAGE_TYPE_CHOICES = [
        ('text', 'Text Message'),
        ('structured', 'Structured Data'),
        ('tool_call', 'Tool Call'),
        ('tool_result', 'Tool Result'),
        ('error', 'Error Message'),
        ('suggestion', 'Suggestion'),
    ]
    
    uuid = models.CharField(
        max_length=17,
        primary_key=True,
        default=generate_chat_uuid,
        editable=False
    )
    
    conversation = models.ForeignKey(
        ChatConversation,
        on_delete=models.CASCADE,
        related_name='messages',
        db_column='conversation_uuid'
    )
    
    # Message metadata
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    message_type = models.CharField(
        max_length=20,
        choices=MESSAGE_TYPE_CHOICES,
        default='text'
    )
    
    # Content
    content = models.TextField()
    content_structured = models.JSONField(
        default=dict,
        blank=True,
        help_text="Structured content (cards, suggestions, etc.)"
    )
    
    # Tool-related fields
    tool_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Name of the tool if this is a tool call/result"
    )
    tool_input = models.JSONField(
        default=dict,
        blank=True,
        help_text="Input parameters for tool calls"
    )
    tool_output = models.JSONField(
        default=dict,
        blank=True,
        help_text="Output from tool execution"
    )
    
    # Agent tracking (for multi-agent systems)
    agent_name = models.CharField(
        max_length=50,
        blank=True,
        help_text="Name of the agent that generated this message"
    )
    agent_reasoning = models.TextField(
        blank=True,
        help_text="Agent's reasoning process (for transparency)"
    )
    
    # Citations and sources
    sources = models.JSONField(
        default=list,
        blank=True,
        help_text="References to data sources (database records, web URLs, etc.)"
    )
    
    # Performance metrics
    tokens_used = models.PositiveIntegerField(null=True, blank=True)
    processing_time_ms = models.PositiveIntegerField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'chat_messages'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
            models.Index(fields=['role']),
            models.Index(fields=['agent_name']),
        ]
    
    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."


class ChatMemory(models.Model):
    """
    Long-term memory storage for the MARK AI.
    
    Stores key facts, preferences, and insights extracted from
    conversations for personalized future interactions.
    """
    
    MEMORY_TYPE_CHOICES = [
        ('preference', 'User Preference'),
        ('business_fact', 'Business Fact'),
        ('brand_attribute', 'Brand Attribute'),
        ('goal', 'Business Goal'),
        ('constraint', 'Constraint/Limitation'),
        ('insight', 'Strategic Insight'),
        ('feedback', 'User Feedback'),
    ]
    
    uuid = models.CharField(
        max_length=17,
        primary_key=True,
        default=generate_chat_uuid,
        editable=False
    )
    
    # User context
    user_id = models.CharField(
        max_length=36,
        null=True,
        blank=True,
        db_index=True
    )
    brand = models.ForeignKey(
        'brand_dna_extractor.Brand',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='chat_memories',
        db_column='brand_uuid'
    )
    
    # Memory content
    memory_type = models.CharField(
        max_length=20,
        choices=MEMORY_TYPE_CHOICES
    )
    key = models.CharField(
        max_length=200,
        help_text="Semantic key for the memory"
    )
    value = models.TextField(help_text="Memory content")
    value_structured = models.JSONField(
        default=dict,
        blank=True,
        help_text="Structured memory data"
    )
    
    # Context
    source_conversation = models.ForeignKey(
        ChatConversation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='extracted_memories'
    )
    confidence_score = models.FloatField(
        default=1.0,
        help_text="Confidence in this memory (0.0-1.0)"
    )
    
    # Lifecycle
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    access_count = models.PositiveIntegerField(default=0)
    last_accessed_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'chat_memories'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user_id', 'memory_type']),
            models.Index(fields=['brand', 'memory_type']),
            models.Index(fields=['key']),
        ]
        unique_together = ['user_id', 'brand', 'key']
    
    def __str__(self):
        return f"{self.memory_type}: {self.key}"


class ChatSuggestion(models.Model):
    """
    Pre-defined suggestions and quick replies for the chat interface.
    """
    
    CATEGORY_CHOICES = [
        ('onboarding', 'Onboarding'),
        ('strategy', 'Strategy'),
        ('content', 'Content Creation'),
        ('analytics', 'Analytics'),
        ('general', 'General'),
        ('brand', 'Brand Management'),
    ]
    
    uuid = models.CharField(
        max_length=17,
        primary_key=True,
        default=generate_chat_uuid,
        editable=False
    )
    
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='general'
    )
    
    suggestion_text = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # Context matching
    required_conversation_type = models.CharField(
        max_length=20,
        choices=ChatConversation.CONVERSATION_TYPE_CHOICES,
        blank=True,
        help_text="Only show in specific conversation types"
    )
    
    # Display settings
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    # Usage tracking
    use_count = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'chat_suggestions'
        ordering = ['category', 'display_order']
    
    def __str__(self):
        return self.suggestion_text
