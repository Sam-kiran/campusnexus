from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('student/', views.student_dashboard, name='student_dashboard'),
    path('admin/', views.admin_dashboard, name='admin_dashboard'),
    path('management/', views.management_dashboard, name='management_dashboard'),
    path('management/payments/', views.payment_export, name='management_payments_export'),
    path('management/payments/event/<int:event_id>/', views.payment_detail, name='management_payment_detail'),
    path('management/payments/list/', views.management_payments_list, name='management_payments_list'),
    path('management/payments/toggle/<int:reg_id>/', views.toggle_payment_verification, name='management_toggle_payment'),
    path('management/payments/approve/<int:reg_id>/', views.approve_payment, name='management_approve_payment'),
    path('leaderboard/', views.leaderboard_view, name='leaderboard'),
    path('export/<str:format_type>/', views.export_report, name='export_report'),
    path('api/analytics/', views.analytics_api, name='analytics_api'),
    path('api/hotness/', views.hotness_api, name='hotness_api'),
]

