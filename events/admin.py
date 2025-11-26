from django.contrib import admin
from .models import Event, Registration, EventRecommendation, PaymentQRCode


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'department', 'event_date', 'status', 'total_registrations', 'hotness_score', 'created_by']
    list_filter = ['status', 'category', 'department', 'event_date', 'is_team_event']
    search_fields = ['title', 'description', 'department']
    readonly_fields = ['created_at', 'updated_at', 'hotness_score', 'average_rating', 'total_registrations']
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'category', 'department', 'banner')
        }),
        ('Event Details', {
            'fields': ('event_date', 'location', 'capacity', 'fee', 'rules')
        }),
        ('Team Settings', {
            'fields': ('is_team_event', 'team_size')
        }),
        ('Payment', {
            'fields': ('qr_code_data', 'qr_code')
        }),
        ('Status & Approval', {
            'fields': ('status', 'created_by', 'approved_by', 'approved_at')
        }),
        ('Statistics', {
            'fields': ('total_registrations', 'average_rating', 'hotness_score')
        }),
    )


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = ['user', 'event', 'payment_status', 'is_verified', 'registered_at']
    list_filter = ['payment_status', 'is_verified', 'registered_at']
    search_fields = ['user__username', 'event__title', 'team_name']
    readonly_fields = ['registered_at', 'verified_at']


@admin.register(EventRecommendation)
class EventRecommendationAdmin(admin.ModelAdmin):
    list_display = ['user', 'event', 'score', 'reason', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'event__title']


@admin.register(PaymentQRCode)
class PaymentQRCodeAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_by', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'qr_code_data']
    readonly_fields = ['created_at', 'updated_at']

