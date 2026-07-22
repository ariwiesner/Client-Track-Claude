from django.contrib import admin

from core.models import (
    Client, GoogleCalendarCredential, Meeting, MonthlyBilling, Notification, PushSubscription,
    Receipt, ReceiptChatUpload, TimeEntry, TrackedSystem,
)


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ['name', 'job_type', 'phone', 'hourly_rate', 'is_active']
    search_fields = ['name']


@admin.register(TrackedSystem)
class TrackedSystemAdmin(admin.ModelAdmin):
    list_display = ['name', 'process_name', 'title_pattern_type', 'is_active']


@admin.register(TimeEntry)
class TimeEntryAdmin(admin.ModelAdmin):
    list_display = ['client', 'employee', 'start_time', 'end_time', 'source', 'status']
    list_filter = ['status', 'source', 'client']
    date_hierarchy = 'start_time'


@admin.register(MonthlyBilling)
class MonthlyBillingAdmin(admin.ModelAdmin):
    list_display = ['client', 'year', 'month', 'total_hours', 'amount_owed', 'paid']
    list_filter = ['paid', 'year', 'month']


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ['client', 'receipt_date', 'category', 'amount', 'receipt_number', 'created_by']
    list_filter = ['category', 'client']
    date_hierarchy = 'receipt_date'


@admin.register(ReceiptChatUpload)
class ReceiptChatUploadAdmin(admin.ModelAdmin):
    list_display = ['created_by', 'status', 'receipt', 'created_at']
    list_filter = ['status', 'created_by']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['category', 'message', 'actor', 'is_read', 'created_at']
    list_filter = ['category', 'is_read']
    date_hierarchy = 'created_at'


@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'endpoint', 'created_at']
    list_filter = ['user']
    date_hierarchy = 'created_at'


@admin.register(Meeting)
class MeetingAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'start_time', 'reminder_minutes_before', 'reminder_sent', 'created_by',
        'google_event_id',
    ]
    list_filter = ['reminder_sent']
    date_hierarchy = 'start_time'


@admin.register(GoogleCalendarCredential)
class GoogleCalendarCredentialAdmin(admin.ModelAdmin):
    list_display = ['user', 'token_expiry', 'updated_at']
