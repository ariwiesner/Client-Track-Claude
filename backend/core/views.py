from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db.models import DurationField, ExpressionWrapper, F, Sum
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from core.models import Client, MonthlyBilling, Receipt, TimeEntry, TrackedSystem
from core.serializers import (
    ClientSerializer,
    CreateWorkerSerializer,
    MonthlyBillingSerializer,
    ReceiptSerializer,
    TimeEntrySerializer,
    TrackedSystemSerializer,
    UserSerializer,
)
from core.services import billing, receipt_llm


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    username = request.data.get('username')
    password = request.data.get('password')
    user = authenticate(username=username, password=password)
    if user is None:
        return Response({'detail': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)
    token, _ = Token.objects.get_or_create(user=user)
    return Response({'token': token.key, 'user': UserSerializer(user).data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me_view(request):
    return Response(UserSerializer(request.user).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password_view(request):
    old_password = request.data.get('old_password')
    new_password = request.data.get('new_password')
    if not request.user.check_password(old_password or ''):
        return Response({'detail': 'הסיסמה הנוכחית שגויה'}, status=status.HTTP_400_BAD_REQUEST)
    if not new_password or len(new_password) < 4:
        return Response(
            {'detail': 'הסיסמה החדשה חייבת להכיל לפחות 4 תווים'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    request.user.set_password(new_password)
    request.user.save()
    return Response({'detail': 'הסיסמה עודכנה בהצלחה'})


def _compute_worker_summary(employee, year, month):
    duration_expr = ExpressionWrapper(
        F('end_time') - F('start_time'), output_field=DurationField()
    )

    hours_by_employee = {
        row['employee_id']: Decimal(row['total'].total_seconds()) / Decimal(3600)
        for row in (
            TimeEntry.objects.filter(
                status=TimeEntry.STATUS_STOPPED, start_time__year=year, start_time__month=month
            )
            .annotate(duration=duration_expr)
            .values('employee_id')
            .annotate(total=Sum('duration'))
        )
        if row['total']
    }

    ranking = sorted(hours_by_employee.items(), key=lambda kv: kv[1], reverse=True)
    rank = next((i + 1 for i, (uid, _) in enumerate(ranking) if uid == employee.id), None)

    breakdown = [
        {
            'client_id': row['client_id'],
            'client_name': row['client__name'],
            'system_name': row['system__name'] or 'ידני',
            'hours': float(Decimal(row['total'].total_seconds()) / Decimal(3600)),
        }
        for row in (
            TimeEntry.objects.filter(
                employee=employee,
                status=TimeEntry.STATUS_STOPPED,
                start_time__year=year,
                start_time__month=month,
            )
            .annotate(duration=duration_expr)
            .values('client_id', 'client__name', 'system__name')
            .annotate(total=Sum('duration'))
            .order_by('-total')
        )
        if row['total']
    ]

    return {
        'total_hours': float(hours_by_employee.get(employee.id, Decimal('0'))),
        'rank': rank,
        'total_workers': len(ranking),
        'is_first_place': rank == 1,
        'breakdown': breakdown,
    }


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_summary_view(request):
    now = timezone.localtime()
    year = int(request.query_params.get('year', now.year))
    month = int(request.query_params.get('month', now.month))
    return Response(_compute_worker_summary(request.user, year, month))


class WorkerViewSet(viewsets.ModelViewSet):
    """Office-admin-only: list/add/edit workers, toggle admin rights, and
    deactivate (never hard-delete — their TimeEntry history must survive).
    """
    http_method_names = ['get', 'post', 'patch', 'delete']
    permission_classes = [IsAdminUser]
    queryset = User.objects.all().order_by('first_name', 'username')

    def get_serializer_class(self):
        return CreateWorkerSerializer if self.action == 'create' else UserSerializer

    def perform_destroy(self, instance):
        if instance.id == self.request.user.id:
            raise ValidationError('אי אפשר להשבית את המשתמש שלך.')
        instance.is_active = False
        instance.save(update_fields=['is_active'])

    def perform_update(self, serializer):
        if serializer.instance.id == self.request.user.id and 'is_staff' in self.request.data:
            raise ValidationError('אי אפשר לשנות את הרשאות המנהל של עצמך.')
        serializer.save()

    @action(detail=True, methods=['get'])
    def summary(self, request, pk=None):
        worker = self.get_object()
        now = timezone.localtime()
        year = int(request.query_params.get('year', now.year))
        month = int(request.query_params.get('month', now.month))
        return Response(_compute_worker_summary(worker, year, month))


class ClientViewSet(viewsets.ModelViewSet):
    serializer_class = ClientSerializer
    queryset = Client.objects.filter(is_active=True)

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=['is_active'])


class TrackedSystemViewSet(viewsets.ModelViewSet):
    serializer_class = TrackedSystemSerializer
    queryset = TrackedSystem.objects.filter(is_active=True)

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=['is_active'])


class TimeEntryViewSet(viewsets.ModelViewSet):
    serializer_class = TimeEntrySerializer

    def get_queryset(self):
        qs = TimeEntry.objects.all()
        client_id = self.request.query_params.get('client')
        employee_id = self.request.query_params.get('employee')
        month = self.request.query_params.get('month')  # format YYYY-MM
        if client_id:
            qs = qs.filter(client_id=client_id)
        if employee_id:
            qs = qs.filter(employee_id=employee_id)
        if month:
            year_str, month_str = month.split('-')
            qs = qs.filter(start_time__year=int(year_str), start_time__month=int(month_str))
        return qs

    @action(detail=False, methods=['get'])
    def current(self, request):
        entry = TimeEntry.objects.filter(
            employee=request.user, status=TimeEntry.STATUS_RUNNING
        ).first()
        if not entry:
            # 204 (not 200 + null body) so clients can rely on status rather
            # than parsing an empty body as JSON.
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(TimeEntrySerializer(entry).data)

    @action(detail=False, methods=['post'])
    def start(self, request):
        if TimeEntry.objects.filter(
            employee=request.user, status=TimeEntry.STATUS_RUNNING
        ).exists():
            return Response(
                {'detail': 'A timer is already running for this employee.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        client_id = request.data.get('client_id')
        client = Client.objects.filter(pk=client_id, is_active=True).first()
        if not client:
            return Response({'detail': 'Unknown client'}, status=status.HTTP_400_BAD_REQUEST)
        source = request.data.get('source', TimeEntry.SOURCE_MANUAL)
        system_id = request.data.get('system_id')
        entry = TimeEntry.objects.create(
            client=client,
            employee=request.user,
            start_time=timezone.now(),
            source=source,
            status=TimeEntry.STATUS_RUNNING,
            system_id=system_id,
        )
        return Response(TimeEntrySerializer(entry).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def stop(self, request, pk=None):
        entry = self.get_object()
        if entry.status != TimeEntry.STATUS_RUNNING:
            return Response({'detail': 'Entry is not running'}, status=status.HTTP_400_BAD_REQUEST)
        entry.end_time = timezone.now()
        entry.status = TimeEntry.STATUS_STOPPED
        entry.save(update_fields=['end_time', 'status', 'updated_at'])
        billing.get_or_refresh_billing(entry.client, entry.start_time.year, entry.start_time.month)
        return Response(TimeEntrySerializer(entry).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        entry = self.get_object()
        if entry.status != TimeEntry.STATUS_RUNNING:
            return Response({'detail': 'Entry is not running'}, status=status.HTTP_400_BAD_REQUEST)
        entry.status = TimeEntry.STATUS_CANCELLED
        entry.end_time = timezone.now()
        entry.save(update_fields=['end_time', 'status', 'updated_at'])
        return Response(TimeEntrySerializer(entry).data)

    @action(detail=True, methods=['post'])
    def resume(self, request, pk=None):
        previous = self.get_object()
        if TimeEntry.objects.filter(
            employee=request.user, status=TimeEntry.STATUS_RUNNING
        ).exists():
            return Response(
                {'detail': 'A timer is already running for this employee.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        entry = TimeEntry.objects.create(
            client=previous.client,
            employee=request.user,
            start_time=timezone.now(),
            source=TimeEntry.SOURCE_MANUAL,
            status=TimeEntry.STATUS_RUNNING,
        )
        return Response(TimeEntrySerializer(entry).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def manual(self, request):
        client_id = request.data.get('client_id')
        date_str = request.data.get('date')  # 'YYYY-MM-DD'
        hours = request.data.get('hours')
        client = Client.objects.filter(pk=client_id, is_active=True).first()
        if not client or not date_str or not hours:
            return Response(
                {'detail': 'client_id, date and hours are required'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        start = timezone.make_aware(
            timezone.datetime.strptime(date_str, '%Y-%m-%d')
        )
        end = start + timedelta(hours=float(hours))
        entry = TimeEntry.objects.create(
            client=client,
            employee=request.user,
            start_time=start,
            end_time=end,
            source=TimeEntry.SOURCE_MANUAL,
            status=TimeEntry.STATUS_STOPPED,
        )
        billing.get_or_refresh_billing(client, start.year, start.month)
        return Response(TimeEntrySerializer(entry).data, status=status.HTTP_201_CREATED)


class MonthlyBillingViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = MonthlyBillingSerializer

    def get_queryset(self):
        now = timezone.localtime()
        year = int(self.request.query_params.get('year', now.year))
        month = int(self.request.query_params.get('month', now.month))
        client_id = self.request.query_params.get('client')

        clients = Client.objects.filter(is_active=True)
        if client_id:
            clients = clients.filter(pk=client_id)

        ids = billing.bulk_get_or_refresh_billing(clients, year, month)
        return MonthlyBilling.objects.filter(id__in=ids)

    @action(detail=True, methods=['post'], url_path='toggle-paid')
    def toggle_paid(self, request, pk=None):
        row = self.get_object()
        row = billing.toggle_paid(row)
        return Response(MonthlyBillingSerializer(row).data)


class ReceiptViewSet(viewsets.ModelViewSet):
    """Available to every worker (default IsAuthenticated) — receipts are
    approved-only by construction: nothing is persisted until the worker
    confirms the fields via /extract/, so no edit/delete in v1.
    """
    http_method_names = ['get', 'post']
    serializer_class = ReceiptSerializer

    def get_queryset(self):
        qs = Receipt.objects.select_related('client', 'created_by')
        client_id = self.request.query_params.get('client')
        year = self.request.query_params.get('year')
        month = self.request.query_params.get('month')
        if client_id:
            qs = qs.filter(client_id=client_id)
        if year:
            qs = qs.filter(receipt_date__year=int(year))
        if month:
            qs = qs.filter(receipt_date__month=int(month))
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['post'])
    def extract(self, request):
        image = request.FILES.get('image')
        if not image:
            return Response({'detail': 'image is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            return Response(receipt_llm.extract_receipt(image))
        except receipt_llm.ExtractionError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
