from rest_framework.routers import DefaultRouter

from django.urls import path

from core.views import (
    ClientViewSet,
    MonthlyBillingViewSet,
    ReceiptViewSet,
    TimeEntryViewSet,
    TrackedSystemViewSet,
    WorkerViewSet,
    change_password_view,
    login_view,
    me_view,
    my_summary_view,
)

router = DefaultRouter()
router.register('clients', ClientViewSet, basename='client')
router.register('systems', TrackedSystemViewSet, basename='trackedsystem')
router.register('time-entries', TimeEntryViewSet, basename='timeentry')
router.register('billing', MonthlyBillingViewSet, basename='monthlybilling')
router.register('workers', WorkerViewSet, basename='worker')
router.register('receipts', ReceiptViewSet, basename='receipt')

urlpatterns = [
    path('auth/login/', login_view, name='login'),
    path('auth/me/', me_view, name='me'),
    path('auth/change-password/', change_password_view, name='change-password'),
    path('me/summary/', my_summary_view, name='me-summary'),
] + router.urls
