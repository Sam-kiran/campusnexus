from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Leaderboard


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'role', 'department', 'is_verified', 'is_active']
    list_filter = ['role', 'is_verified', 'is_active', 'department']
    search_fields = ['username', 'email', 'student_id']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': ('role', 'department', 'student_id', 'phone_number', 'profile_picture', 'is_verified')
        }),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Additional Info', {
            'fields': ('role', 'email', 'department', 'student_id', 'phone_number')
        }),
    )


@admin.register(Leaderboard)
class LeaderboardAdmin(admin.ModelAdmin):
    list_display = ['user', 'rank', 'total_points', 'total_events_attended', 'total_feedback_given']
    list_filter = ['rank']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['updated_at']

