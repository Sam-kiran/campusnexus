from django.urls import path
from . import views

app_name = 'events'

urlpatterns = [
    path('', views.event_list, name='event_list'),
    path('<int:event_id>/', views.event_detail, name='event_detail'),
    path('create/', views.event_create, name='event_create'),
    path('<int:event_id>/edit/', views.event_edit, name='event_edit'),
    path('<int:event_id>/delete/', views.event_delete, name='event_delete'),
    path('<int:event_id>/approve/', views.event_approve, name='event_approve'),
    path('<int:event_id>/reject/', views.event_reject, name='event_reject'),
    path('<int:event_id>/register/', views.event_register, name='event_register'),
    path('registration/<int:registration_id>/verify/', views.verify_payment, name='verify_payment'),
    path('api/hot-events/', views.hot_events_api, name='hot_events_api'),
    path('api/recommendations/', views.recommendations_api, name='recommendations_api'),
    path('api/sentiment/', views.sentiment_analysis_api, name='sentiment_api'),
]

