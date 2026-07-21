import threading

from django.utils import timezone

from core.models import Notification, TimeEntry
from core.services import push

PANEL_SIZE = 20


def _display_name(user):
    if not user:
        return 'משתמש לא ידוע'
    return user.first_name or user.username


def _source_label(source):
    return 'אוטומטי' if source == TimeEntry.SOURCE_AUTO else 'ידני'


def create_notification(category, message, actor=None):
    notification = Notification.objects.create(category=category, message=message, actor=actor)
    # Fire-and-forget: a third-party push service hiccup must never slow
    # down or break the action that triggered this notification (gunicorn
    # runs sync workers, so an inline call here would block the whole
    # request on push-service latency for every user, not just the
    # superuser who actually receives the push).
    threading.Thread(target=push.send_push, args=(notification,), daemon=True).start()
    return notification


def notify_sign_in(entry):
    create_notification(
        Notification.CATEGORY_SIGN_IN,
        f'{_display_name(entry.employee)} נכנס/ה לשעון עבור {entry.client.name}',
        actor=entry.employee,
    )


def notify_sign_out(entry):
    create_notification(
        Notification.CATEGORY_SIGN_OUT,
        f'{_display_name(entry.employee)} יצא/ה משעון עבור {entry.client.name} '
        f'({entry.duration_hours:.2f} שעות, {_source_label(entry.source)})',
        actor=entry.employee,
    )


def notify_hours_added(entry):
    create_notification(
        Notification.CATEGORY_HOURS,
        f'{_display_name(entry.employee)} רשם/ה {entry.duration_hours:.2f} שעות '
        f'עבור {entry.client.name} ({_source_label(entry.source)})',
        actor=entry.employee,
    )


def notify_receipt_added(receipt):
    create_notification(
        Notification.CATEGORY_RECEIPT,
        f'{_display_name(receipt.created_by)} הוסיף/ה קבלה עבור {receipt.client.name} '
        f'על סך ₪{receipt.amount}',
        actor=receipt.created_by,
    )


def notify_login(user):
    # The only viewer of this feed is the superuser, so when they're the one
    # logging in, phrase it in 2nd person rather than showing their own name
    # in the third person.
    message = 'אתה התחברת למערכת' if user.is_superuser else f'{_display_name(user)} התחבר/ה למערכת'
    create_notification(Notification.CATEGORY_LOGIN, message, actor=user)


def notify_logout(user):
    message = 'אתה התנתקת מהמערכת' if user.is_superuser else f'{_display_name(user)} התנתק/ה מהמערכת'
    create_notification(Notification.CATEGORY_LOGOUT, message, actor=user)


def notify_billing_toggled(billing, actor=None):
    status_label = 'שולם' if billing.paid else 'לא שולם'
    create_notification(
        Notification.CATEGORY_BILLING,
        f'החיוב של {billing.client.name} עבור {billing.month:02d}/{billing.year} '
        f'סומן כ{status_label}',
        actor=actor,
    )


def notify_meeting_reminder(meeting):
    when = timezone.localtime(meeting.start_time).strftime('%H:%M')
    create_notification(
        Notification.CATEGORY_MEETING_REMINDER,
        f'תזכורת: פגישה "{meeting.title}" בשעה {when}',
        actor=meeting.created_by,
    )
