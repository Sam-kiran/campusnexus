from django.urls import path
from . import views

app_name = 'feedback'

urlpatterns = [
    path('event/<int:event_id>/create/', views.feedback_create, name='feedback_create'),
    path('event/<int:event_id>/list/', views.feedback_list, name='feedback_list'),
    path('api/event/<int:event_id>/stats/', views.feedback_stats_api, name='feedback_stats_api'),
]

