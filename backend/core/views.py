import os
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.db.models import DurationField, ExpressionWrapper, F, Sum
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from core.models import Client, MonthlyBilling, Receipt, ReceiptChatUpload, TimeEntry, TrackedSystem
from core.serializers import (
    ClientSerializer,
    CreateWorkerSerializer,
    MonthlyBillingSerializer,
    ReceiptChatUploadSerializer,
    ReceiptSerializer,
    TimeEntrySerializer,
    TrackedSystemSerializer,
    UserSerializer,
)
from core.services import billing, receipt_llm

RECEIPT_CHAT_RETENTION_DAYS = 7


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
    """Available to every worker (default IsAuthenticated). Approved
    receipts are permanent — creation normally happens via
    ReceiptChatViewSet.approve, not directly against this endpoint.
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


class ReceiptChatViewSet(viewsets.ModelViewSet):
    """A worker's personal receipt-chat history — every upload attempt
    (pending review, approved, discarded, or failed extraction), kept for
    RECEIPT_CHAT_RETENTION_DAYS so navigating away and back still shows
    what was uploaded. Scoped to request.user; no shared/team visibility
    (approved receipts themselves are shared, via ReceiptViewSet).
    """
    http_method_names = ['get', 'post']
    serializer_class = ReceiptChatUploadSerializer

    def get_queryset(self):
        cutoff = timezone.now() - timedelta(days=RECEIPT_CHAT_RETENTION_DAYS)
        stale = ReceiptChatUpload.objects.filter(created_by=self.request.user, created_at__lt=cutoff)
        for upload in stale:
            upload.image.delete(save=False)
            upload.delete()
        return ReceiptChatUpload.objects.filter(created_by=self.request.user).select_related('receipt')

    def create(self, request, *args, **kwargs):
        image = request.FILES.get('image')
        if not image:
            return Response({'detail': 'image is required'}, status=status.HTTP_400_BAD_REQUEST)

        file_bytes = image.read()
        image.seek(0)

        if not receipt_llm.is_pdf_bytes(file_bytes):
            return self._create_from_extraction(request, image, lambda: receipt_llm.extract_receipt(image))

        try:
            page_count = receipt_llm.count_pdf_pages(file_bytes)
        except Exception:  # noqa: BLE001 — any PDF parsing failure is just a bad file
            return Response({'detail': 'קובץ ה-PDF פגום או לא נתמך'}, status=status.HTTP_400_BAD_REQUEST)

        if page_count > 1:
            # Don't extract yet — could be several separate receipts bundled
            # into one file (e.g. a multi-visit statement) rather than one
            # receipt spanning multiple pages. Ask the worker first; see
            # resolve_pages for what happens with their answer.
            upload = ReceiptChatUpload.objects.create(
                created_by=request.user, image=image,
                status=ReceiptChatUpload.STATUS_AWAITING_PAGE_CHOICE,
                page_count=page_count,
            )
            return Response(self.get_serializer(upload).data, status=status.HTTP_201_CREATED)

        # Single-page PDF: exactly like a normal one-receipt upload, just
        # read via the PDF path (Gemini reads PDFs natively) instead of the
        # photo-preprocessing one.
        return self._create_from_extraction(
            request, image, lambda: receipt_llm.extract_receipt_from_pdf(file_bytes)
        )

    def _create_from_extraction(self, request, image, extract_fn):
        try:
            extraction = extract_fn()
            upload_status = ReceiptChatUpload.STATUS_PENDING
            error_message = ''
        except receipt_llm.ExtractionError as exc:
            extraction = {}
            upload_status = ReceiptChatUpload.STATUS_ERROR
            error_message = str(exc)

        image.seek(0)
        upload = ReceiptChatUpload.objects.create(
            created_by=request.user, image=image, status=upload_status,
            extraction=extraction, error_message=error_message,
        )
        return Response(self.get_serializer(upload).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='resolve-pages')
    def resolve_pages(self, request, pk=None):
        upload = self.get_object()
        if upload.status != ReceiptChatUpload.STATUS_AWAITING_PAGE_CHOICE:
            return Response({'detail': 'קובץ זה כבר טופל'}, status=status.HTTP_400_BAD_REQUEST)

        split = str(request.data.get('split', '')).lower() in ('1', 'true', 'yes')

        upload.image.open('rb')
        pdf_bytes = upload.image.read()
        upload.image.close()

        if not split:
            # One receipt spanning multiple pages — extract from the whole
            # PDF at once so fields split across pages (e.g. items on page
            # 1, total/signature on page 2) are all visible together.
            try:
                upload.extraction = receipt_llm.extract_receipt_from_pdf(pdf_bytes)
                upload.status = ReceiptChatUpload.STATUS_PENDING
                upload.error_message = ''
            except receipt_llm.ExtractionError as exc:
                upload.status = ReceiptChatUpload.STATUS_ERROR
                upload.error_message = str(exc)
            upload.page_count = None
            upload.save(update_fields=['status', 'extraction', 'error_message', 'page_count'])
            return Response({'entries': [self.get_serializer(upload).data]})

        # Several separate receipts: rasterize each page and run it through
        # the normal single-receipt pipeline as its own chat entry.
        created = []
        for page_index in range(upload.page_count or 0):
            page_png = receipt_llm.render_pdf_page_to_png(pdf_bytes, page_index)
            page_file = ContentFile(page_png, name=f'page-{page_index + 1}.png')
            try:
                extraction = receipt_llm.extract_receipt(page_file)
                page_status = ReceiptChatUpload.STATUS_PENDING
                error_message = ''
            except receipt_llm.ExtractionError as exc:
                extraction = {}
                page_status = ReceiptChatUpload.STATUS_ERROR
                error_message = str(exc)
            page_file.seek(0)
            created.append(ReceiptChatUpload.objects.create(
                created_by=request.user, image=page_file, status=page_status,
                extraction=extraction, error_message=error_message,
            ))

        upload.image.delete(save=False)
        upload.delete()

        return Response({'entries': self.get_serializer(created, many=True).data})

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        upload = self.get_object()
        if upload.status != ReceiptChatUpload.STATUS_PENDING:
            return Response({'detail': 'הקבלה כבר טופלה'}, status=status.HTTP_400_BAD_REQUEST)

        client = Client.objects.filter(pk=request.data.get('client'), is_active=True).first()
        if not client:
            return Response({'detail': 'יש לבחור לקוח'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            amount = Decimal(str(request.data.get('amount')))
        except (InvalidOperation, TypeError, ValueError):
            return Response({'detail': 'סכום לא תקין'}, status=status.HTTP_400_BAD_REQUEST)

        category = request.data.get('category')
        if category not in {value for value, _label in Receipt.CATEGORY_CHOICES}:
            return Response({'detail': 'קטגוריה לא תקינה'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            receipt_date = date.fromisoformat(request.data.get('receipt_date', ''))
        except ValueError:
            return Response({'detail': 'תאריך לא תקין'}, status=status.HTTP_400_BAD_REQUEST)

        receipt_number = request.data.get('receipt_number', '')
        force = str(request.data.get('force', '')).lower() in ('1', 'true', 'yes')

        if not force:
            existing = Receipt.objects.filter(client=client)
            duplicate = None
            if receipt_number:
                duplicate = existing.filter(receipt_number=receipt_number).first()
            if not duplicate:
                duplicate = existing.filter(amount=amount, receipt_date=receipt_date).first()
            if duplicate:
                return Response(
                    {'duplicate': True, 'existing_receipt': ReceiptSerializer(
                        duplicate, context=self.get_serializer_context()
                    ).data},
                    status=status.HTTP_409_CONFLICT,
                )

        receipt = Receipt(
            client=client,
            amount=amount,
            receipt_number=receipt_number,
            category=category,
            receipt_date=receipt_date,
            created_by=request.user,
        )
        upload.image.open('rb')
        receipt.image.save(os.path.basename(upload.image.name), ContentFile(upload.image.read()), save=False)
        upload.image.close()
        receipt.save()

        upload.status = ReceiptChatUpload.STATUS_APPROVED
        upload.receipt = receipt
        upload.save(update_fields=['status', 'receipt'])

        return Response(self.get_serializer(upload).data)

    @action(detail=True, methods=['post'])
    def discard(self, request, pk=None):
        upload = self.get_object()
        if upload.status != ReceiptChatUpload.STATUS_PENDING:
            return Response({'detail': 'הקבלה כבר טופלה'}, status=status.HTTP_400_BAD_REQUEST)
        upload.status = ReceiptChatUpload.STATUS_DISCARDED
        upload.save(update_fields=['status'])
        return Response(self.get_serializer(upload).data)

    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        upload = self.get_object()
        if upload.status != ReceiptChatUpload.STATUS_ERROR:
            return Response({'detail': 'ניתן לנסות שוב רק קבלה שנכשלה'}, status=status.HTTP_400_BAD_REQUEST)

        upload.image.open('rb')
        try:
            upload.extraction = receipt_llm.extract_receipt(upload.image)
            upload.status = ReceiptChatUpload.STATUS_PENDING
            upload.error_message = ''
        except receipt_llm.ExtractionError as exc:
            upload.error_message = str(exc)
        finally:
            upload.image.close()
        upload.save(update_fields=['status', 'extraction', 'error_message'])
        return Response(self.get_serializer(upload).data)
