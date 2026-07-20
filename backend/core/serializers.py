from django.contrib.auth.models import User
from rest_framework import serializers

from core.models import Client, MonthlyBilling, Receipt, TimeEntry, TrackedSystem


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'is_staff', 'is_active']


class CreateWorkerSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=4)

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'password']

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data['username'],
            first_name=validated_data.get('first_name', ''),
            password=validated_data['password'],
        )

    def to_representation(self, instance):
        # Respond with the same shape as UserSerializer (adds is_staff, drops
        # the write-only password) so the frontend can reuse one User type.
        return UserSerializer(instance).data


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = [
            'id', 'name', 'job_type', 'phone', 'contact_person', 'notes',
            'hourly_rate', 'is_active', 'created_at',
            'case_number', 'tax_subject', 'unit', 'sub_case', 'representative',
            'representation_start', 'validity_91', 'bank_details',
        ]


class TrackedSystemSerializer(serializers.ModelSerializer):
    # DRF's CharField trims leading/trailing whitespace by default, which
    # would silently corrupt a delimiter like " - " into "-".
    title_delimiter = serializers.CharField(
        max_length=50, required=False, allow_blank=True, trim_whitespace=False
    )

    class Meta:
        model = TrackedSystem
        fields = [
            'id', 'name', 'process_name', 'title_pattern_type',
            'title_delimiter', 'title_delimiter_index', 'title_regex',
            'is_active', 'created_at',
        ]


class TimeEntrySerializer(serializers.ModelSerializer):
    employee = UserSerializer(read_only=True)
    client_name = serializers.CharField(source='client.name', read_only=True)
    system_name = serializers.SerializerMethodField()
    duration_hours = serializers.DecimalField(
        max_digits=8, decimal_places=2, read_only=True
    )

    class Meta:
        model = TimeEntry
        fields = [
            'id', 'client', 'client_name', 'employee', 'start_time', 'end_time',
            'source', 'status', 'system', 'system_name', 'duration_hours',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['start_time', 'end_time', 'status']

    def get_system_name(self, obj):
        return obj.system.name if obj.system else None


class MonthlyBillingSerializer(serializers.ModelSerializer):
    client = ClientSerializer(read_only=True)

    class Meta:
        model = MonthlyBilling
        fields = [
            'id', 'client', 'year', 'month', 'total_hours', 'amount_owed',
            'paid', 'paid_at',
        ]


class ReceiptSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.name', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Receipt
        fields = [
            'id', 'client', 'client_name', 'amount', 'receipt_number',
            'category', 'category_display', 'receipt_date', 'image',
            'created_by_name', 'created_at',
        ]
        read_only_fields = ['created_at']

    def get_created_by_name(self, obj):
        if not obj.created_by:
            return None
        return obj.created_by.first_name or obj.created_by.username
