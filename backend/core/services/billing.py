from decimal import Decimal

from django.db.models import Sum, F, ExpressionWrapper, DurationField
from django.utils import timezone

from core.models import Client, MonthlyBilling, TimeEntry


def compute_hours_for_month(client: Client, year: int, month: int) -> Decimal:
    """Sum stopped TimeEntry durations for this client in the given month."""
    duration_expr = ExpressionWrapper(
        F('end_time') - F('start_time'), output_field=DurationField()
    )
    result = (
        TimeEntry.objects.filter(
            client=client,
            status=TimeEntry.STATUS_STOPPED,
            start_time__year=year,
            start_time__month=month,
        )
        .annotate(duration=duration_expr)
        .aggregate(total=Sum('duration'))
    )
    total_duration = result['total']
    if not total_duration:
        return Decimal('0')
    return Decimal(total_duration.total_seconds()) / Decimal(3600)


def bulk_get_or_refresh_billing(clients, year: int, month: int) -> list[int]:
    """Like get_or_refresh_billing, but for many clients in a handful of queries
    instead of one round-trip per client. Returns the MonthlyBilling ids."""
    clients = list(clients)
    if not clients:
        return []

    existing = {
        row.client_id: row
        for row in MonthlyBilling.objects.filter(client__in=clients, year=year, month=month)
    }

    missing_clients = [c for c in clients if c.id not in existing]
    if missing_clients:
        MonthlyBilling.objects.bulk_create(
            [MonthlyBilling(client=c, year=year, month=month) for c in missing_clients]
        )
        existing = {
            row.client_id: row
            for row in MonthlyBilling.objects.filter(client__in=clients, year=year, month=month)
        }

    duration_expr = ExpressionWrapper(
        F('end_time') - F('start_time'), output_field=DurationField()
    )
    hours_by_client = {
        row['client_id']: Decimal(row['total'].total_seconds()) / Decimal(3600)
        for row in (
            TimeEntry.objects.filter(
                client__in=clients,
                status=TimeEntry.STATUS_STOPPED,
                start_time__year=year,
                start_time__month=month,
            )
            .annotate(duration=duration_expr)
            .values('client_id')
            .annotate(total=Sum('duration'))
        )
        if row['total']
    }

    rate_by_client = {c.id: c.hourly_rate for c in clients}
    to_update = []
    for row in existing.values():
        if row.paid:
            continue
        hours = hours_by_client.get(row.client_id, Decimal('0'))
        row.total_hours = hours
        row.amount_owed = hours * rate_by_client[row.client_id]
        to_update.append(row)
    if to_update:
        MonthlyBilling.objects.bulk_update(to_update, ['total_hours', 'amount_owed'])

    return [row.id for row in existing.values()]


def get_or_refresh_billing(client: Client, year: int, month: int) -> MonthlyBilling:
    """Get (creating if needed) the MonthlyBilling row for client/year/month.

    Live-recomputes hours/amount unless the month is already marked paid,
    in which case the snapshot is left frozen as the historical record.
    """
    billing, _ = MonthlyBilling.objects.get_or_create(
        client=client, year=year, month=month
    )
    if not billing.paid:
        hours = compute_hours_for_month(client, year, month)
        billing.total_hours = hours
        billing.amount_owed = hours * client.hourly_rate
        billing.save(update_fields=['total_hours', 'amount_owed'])
    return billing


def toggle_paid(billing: MonthlyBilling) -> MonthlyBilling:
    billing.paid = not billing.paid
    billing.paid_at = timezone.now() if billing.paid else None
    # Refresh the snapshot either way: freezes current figures when locking,
    # and returns up-to-date figures immediately when unlocking (rather than
    # leaving the stale frozen snapshot until the next read).
    hours = compute_hours_for_month(billing.client, billing.year, billing.month)
    billing.total_hours = hours
    billing.amount_owed = hours * billing.client.hourly_rate
    billing.save()
    return billing


def recalculate(billing: MonthlyBilling) -> MonthlyBilling:
    """Force-refresh a billing row's snapshot regardless of paid status."""
    hours = compute_hours_for_month(billing.client, billing.year, billing.month)
    billing.total_hours = hours
    billing.amount_owed = hours * billing.client.hourly_rate
    billing.save(update_fields=['total_hours', 'amount_owed'])
    return billing
