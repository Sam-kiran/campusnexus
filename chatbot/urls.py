from django.urls import path
from . import views
from .gmail_integration import gmail_pubsub_push

app_name = 'chatbot'

urlpatterns = [
    path('', views.chatbot_view, name='chatbot'),
    path('assistant/', views.ai_assistant_view, name='ai_assistant'),
    path('api/query/', views.chatbot_query, name='chatbot_query'),
    path('api/create-event/', views.create_event_with_ai, name='create_event_ai'),
    path('api/generate-poster/', views.generate_poster_with_ai, name='generate_poster_ai'),
    path('gmail/pubsub/push/', gmail_pubsub_push, name='gmail_pubsub_push'),
]

