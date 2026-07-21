from rest_framework.permissions import BasePermission


class IsSuperUser(BasePermission):
    """Like DRF's IsAdminUser, but checks the true Django superuser flag.
    This app already uses is_staff for the broader "office manager" role
    (see WorkerViewSet) — superuser is a separate, narrower concept.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_superuser)
