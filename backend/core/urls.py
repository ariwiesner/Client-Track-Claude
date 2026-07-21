from rest_framework.routers import DefaultRouter

from django.urls import path

from core.views import (
    ClientViewSet,
    MeetingViewSet,
    MonthlyBillingViewSet,
    NotificationViewSet,
    ReceiptChatViewSet,
    ReceiptViewSet,
    TimeEntryViewSet,
    TrackedSystemViewSet,
    WorkerViewSet,
    change_password_view,
    login_view,
    logout_view,
    me_view,
    my_summary_view,
    push_subscribe_view,
)

router = DefaultRouter()
router.register('clients', ClientViewSet, basename='client')
router.register('systems', TrackedSystemViewSet, basename='trackedsystem')
router.register('time-entries', TimeEntryViewSet, basename='timeentry')
router.register('billing', MonthlyBillingViewSet, basename='monthlybilling')
router.register('workers', WorkerViewSet, basename='worker')
router.register('receipts', ReceiptViewSet, basename='receipt')
router.register('receipt-chat', ReceiptChatViewSet, basename='receiptchatupload')
router.register('notifications', NotificationViewSet, basename='notification')
router.register('meetings', MeetingViewSet, basename='meeting')

urlpatterns = [
    path('auth/login/', login_view, name='login'),
    path('auth/logout/', logout_view, name='logout'),
    path('auth/me/', me_view, name='me'),
    path('auth/change-password/', change_password_view, name='change-password'),
    path('me/summary/', my_summary_view, name='me-summary'),
    path('push/subscribe/', push_subscribe_view, name='push-subscribe'),
] + router.urls
