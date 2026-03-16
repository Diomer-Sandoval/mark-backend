"""
URLs for AI Chatbot API.
"""

from django.urls import path
from . import views

urlpatterns = [
    # Conversations
    path('conversations/', 
         views.ChatConversationListView.as_view(), 
         name='chat-conversation-list'),
    path('conversations/<str:uuid>/', 
         views.ChatConversationDetailView.as_view(), 
         name='chat-conversation-detail'),
    path('conversations/<str:conversation_uuid>/messages/', 
         views.ChatMessageListView.as_view(), 
         name='chat-message-list'),
    
    # Interactions
    path('chat/send/', 
         views.ChatSendMessageView.as_view(), 
         name='chat-send'),
    path('chat/suggestions/', 
         views.ChatSuggestionsView.as_view(), 
         name='chat-suggestions'),
    path('chat/memories/', 
         views.ChatMemoryListView.as_view(), 
         name='chat-memory-list'),
    path('chat/actions/<str:action>/',
         views.ChatQuickActionView.as_view(),
         name='chat-quick-action'),

    # Streaming (SSE)
    path('chat/conversations/<str:conversation_uuid>/stream/',
         views.ChatStreamMessageView.as_view(),
         name='chat-stream'),

    # Direct image generation
    path('chat/generate-image/',
         views.ChatGenerateImageView.as_view(),
         name='chat-generate-image'),

    # Direct content pipeline
    path('content/pipeline/',
         views.ContentPipelineView.as_view(),
         name='content-pipeline'),
 ]
