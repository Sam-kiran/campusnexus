from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('student/', views.student_dashboard, name='student_dashboard'),
    path('admin/', views.admin_dashboard, name='admin_dashboard'),
    path('management/', views.management_dashboard, name='management_dashboard'),
    path('leaderboard/', views.leaderboard_view, name='leaderboard'),
    path('export/<str:format_type>/', views.export_report, name='export_report'),
    path('api/analytics/', views.analytics_api, name='analytics_api'),
]

