from django.contrib import admin

from core.models import Client, MonthlyBilling, Receipt, TimeEntry, TrackedSystem


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
