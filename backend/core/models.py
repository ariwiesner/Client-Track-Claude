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
    # FileField, not ImageField: a receipt may be a photo or a PDF.
    image = models.FileField(upload_to='receipts/%Y/%m/', verbose_name='תמונת הקבלה')
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
    STATUS_AWAITING_PAGE_CHOICE = 'awaiting_page_choice'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'ממתין'),
        (STATUS_APPROVED, 'אושר'),
        (STATUS_DISCARDED, 'בוטל'),
        (STATUS_ERROR, 'שגיאה'),
        (STATUS_AWAITING_PAGE_CHOICE, 'ממתין לבחירת עמודים'),
    ]

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='receipt_chat_uploads'
    )
    # FileField, not ImageField: a receipt may be a photo or a PDF.
    image = models.FileField(upload_to='receipt_chat/%Y/%m/')
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default=STATUS_PENDING)
    extraction = models.JSONField(default=dict, blank=True)
    error_message = models.CharField(max_length=500, blank=True)
    # Only set for a multi-page PDF sitting in STATUS_AWAITING_PAGE_CHOICE —
    # how many pages it has, so the frontend can ask "is this N separate
    # receipts, or one?" without re-opening the file itself.
    page_count = models.PositiveIntegerField(null=True, blank=True)
    receipt = models.ForeignKey(
        Receipt, on_delete=models.SET_NULL, null=True, blank=True, related_name='chat_uploads'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name_plural = 'Receipt chat uploads'

    def __str__(self):
        return f"{self.created_by} — {self.status} — {self.created_at:%Y-%m-%d %H:%M}"


class Notification(models.Model):
    """Superuser-only activity feed. Messages are stored pre-rendered in
    Hebrew at creation time — this app has no i18n layer, so the frontend
    is a pure list-renderer, matching every other user-facing string here.
    """
    CATEGORY_SIGN_IN = 'sign_in'
    CATEGORY_SIGN_OUT = 'sign_out'
    CATEGORY_HOURS = 'hours'
    CATEGORY_RECEIPT = 'receipt'
    CATEGORY_BILLING = 'billing'
    CATEGORY_LOGIN = 'login'
    CATEGORY_LOGOUT = 'logout'
    CATEGORY_MEETING_REMINDER = 'meeting_reminder'
    CATEGORY_CHOICES = [
        (CATEGORY_SIGN_IN, 'כניסה לשעון'),
        (CATEGORY_SIGN_OUT, 'יציאה משעון'),
        (CATEGORY_HOURS, 'שעות'),
        (CATEGORY_RECEIPT, 'קבלה'),
        (CATEGORY_BILLING, 'חיוב'),
        (CATEGORY_LOGIN, 'התחברות'),
        (CATEGORY_LOGOUT, 'התנתקות'),
        (CATEGORY_MEETING_REMINDER, 'תזכורת פגישה'),
    ]

    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    message = models.CharField(max_length=500)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+'
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Notifications'

    def __str__(self):
        return f"{self.category} — {self.created_at:%Y-%m-%d %H:%M} — {self.message[:40]}"


class PushSubscription(models.Model):
    """A single browser/device's Web Push registration. endpoint (not user)
    is the unique key since one person has multiple devices.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='push_subscriptions'
    )
    endpoint = models.URLField(max_length=500, unique=True)
    p256dh = models.CharField(max_length=255)
    auth = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Push subscriptions'

    def __str__(self):
        return f"{self.user} — {self.endpoint[:60]}"


class Meeting(models.Model):
    """A meeting dad schedules for a day/hour. Visible read-only to every
    worker; only he (is_superuser) can create/edit/delete one.
    reminder_sent makes the periodic reminder check idempotent — it's set
    once the lead-time notification has fired, so the same meeting is never
    reminded twice.
    """
    title = models.CharField(max_length=200)
    notes = models.TextField(blank=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    reminder_minutes_before = models.PositiveIntegerField(default=15)
    reminder_sent = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+'
    )
    attendees = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name='meetings'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['start_time']

    def __str__(self):
        return f"{self.title} — {self.start_time:%Y-%m-%d %H:%M}"
