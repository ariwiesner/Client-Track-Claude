from decimal import Decimal

from django.conf import settings
from django.db import models


class Client(models.Model):
    name = models.CharField(max_length=200, unique=True)
    job_type = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    contact_person = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    hourly_rate = models.DecimalField(max_digits=8, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    case_number = models.CharField(max_length=50, blank=True, verbose_name='מספר תיק')
    tax_subject = models.CharField(max_length=100, blank=True, verbose_name='נושא מס')
    unit = models.CharField(max_length=50, blank=True, verbose_name='חוליה')
    sub_case = models.CharField(max_length=50, blank=True, verbose_name='ס.תיק')
    representative = models.CharField(max_length=100, blank=True, verbose_name='מייצג')
    representation_start = models.CharField(max_length=20, blank=True, verbose_name='תחילת ייצוג')
    validity_91 = models.CharField(max_length=50, blank=True, verbose_name='תוקף 91')
    bank_details = models.CharField(max_length=100, blank=True, verbose_name='פרטי בנק')

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class TrackedSystem(models.Model):
    DELIMITER = 'delimiter'
    REGEX = 'regex'
    TITLE_PATTERN_CHOICES = [
        (DELIMITER, 'Delimiter'),
        (REGEX, 'Regex'),
    ]

    name = models.CharField(
        max_length=200,
        help_text="What to look for in open window titles, e.g. 'Google Translate' or 'Netflix'",
    )
    process_name = models.CharField(
        max_length=200, blank=True,
        help_text=(
            "Optional: restrict detection to a specific executable, e.g. 'hashav.exe'. "
            "Leave blank to match this system's name in any open window's title, "
            "whether it's a browser tab or a standalone app."
        ),
    )
    title_pattern_type = models.CharField(
        max_length=20, choices=TITLE_PATTERN_CHOICES, default=DELIMITER
    )
    title_delimiter = models.CharField(
        max_length=50, blank=True,
        help_text="e.g. ' - ' to split 'ClientName - System' window titles",
    )
    title_delimiter_index = models.PositiveIntegerField(
        default=0,
        help_text="Which segment after splitting on the delimiter holds the client name",
    )
    title_regex = models.CharField(
        max_length=500, blank=True,
        help_text="Regex with a named group 'client', e.g. r'^(?P<client>.+?) - Hashav$'",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class TimeEntry(models.Model):
    SOURCE_MANUAL = 'manual'
    SOURCE_AUTO = 'auto'
    SOURCE_CHOICES = [
        (SOURCE_MANUAL, 'Manual'),
        (SOURCE_AUTO, 'Auto'),
    ]

    STATUS_RUNNING = 'running'
    STATUS_STOPPED = 'stopped'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (STATUS_RUNNING, 'Running'),
        (STATUS_STOPPED, 'Stopped'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='time_entries')
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='time_entries'
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default=SOURCE_MANUAL)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_RUNNING)
    system = models.ForeignKey(
        TrackedSystem, on_delete=models.SET_NULL, null=True, blank=True, related_name='time_entries'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_time']
        verbose_name_plural = 'Time entries'

    def __str__(self):
        return f"{self.client} — {self.employee} — {self.start_time:%Y-%m-%d %H:%M}"

    @property
    def duration_hours(self) -> Decimal:
        if self.status != self.STATUS_STOPPED or not self.end_time:
            return Decimal('0')
        seconds = (self.end_time - self.start_time).total_seconds()
        return Decimal(seconds) / Decimal(3600)


class MonthlyBilling(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='monthly_billings')
    year = models.PositiveIntegerField()
    month = models.PositiveSmallIntegerField()
    total_hours = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    amount_owed = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    paid = models.BooleanField(default=False)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('client', 'year', 'month')
        ordering = ['-year', '-month']
        verbose_name_plural = 'Monthly billings'

    def __str__(self):
        return f"{self.client} — {self.year}-{self.month:02d}"


class Receipt(models.Model):
    CATEGORY_FOOD = 'food'
    CATEGORY_OFFICE_SUPPLIES = 'office_supplies'
    CATEGORY_TRAVEL = 'travel'
    CATEGORY_BUSINESS = 'business'
    CATEGORY_OTHER = 'other'
    CATEGORY_CHOICES = [
        (CATEGORY_FOOD, 'מזון'),
        (CATEGORY_OFFICE_SUPPLIES, 'ציוד משרדי'),
        (CATEGORY_TRAVEL, 'נסיעות'),
        (CATEGORY_BUSINESS, 'עבור העסק'),
        (CATEGORY_OTHER, 'אחר'),
    ]

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='receipts')
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='סכום')
    receipt_number = models.CharField(max_length=100, blank=True, verbose_name='מספר קבלה')
    category = models.CharField(
        max_length=20, choices=CATEGORY_CHOICES, default=CATEGORY_OTHER, verbose_name='קטגוריה'
    )
    receipt_date = models.DateField(verbose_name='תאריך הקבלה')
    image = models.ImageField(upload_to='receipts/%Y/%m/', verbose_name='תמונת הקבלה')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='receipts'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-receipt_date', '-created_at']
        verbose_name_plural = 'Receipts'

    def __str__(self):
        return f"{self.client} — {self.receipt_date} — ₪{self.amount}"


class ReceiptChatUpload(models.Model):
    """One turn in a worker's receipt-chat: the uploaded photo plus what the
    LLM extracted from it. Kept (unlike Receipt) even before/without
    approval, so the chat has something to show when the worker navigates
    back — see ReceiptChatViewSet's lazy 7-day cleanup for retention.
    """
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_DISCARDED = 'discarded'
    STATUS_ERROR = 'error'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'ממתין'),
        (STATUS_APPROVED, 'אושר'),
        (STATUS_DISCARDED, 'בוטל'),
        (STATUS_ERROR, 'שגיאה'),
    ]

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='receipt_chat_uploads'
    )
    image = models.ImageField(upload_to='receipt_chat/%Y/%m/')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    extraction = models.JSONField(default=dict, blank=True)
    error_message = models.CharField(max_length=500, blank=True)
    receipt = models.ForeignKey(
        Receipt, on_delete=models.SET_NULL, null=True, blank=True, related_name='chat_uploads'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name_plural = 'Receipt chat uploads'

    def __str__(self):
        return f"{self.created_by} — {self.status} — {self.created_at:%Y-%m-%d %H:%M}"
