from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsSuperUser(BasePermission):
    """Like DRF's IsAdminUser, but checks the true Django superuser flag.
    This app already uses is_staff for the broader "office manager" role
    (see WorkerViewSet) — superuser is a separate, narrower concept.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_superuser)


class IsSuperUserOrReadOnly(BasePermission):
    """Any authenticated worker can view (e.g. the meetings calendar); only
    the superuser (dad) can create/edit/delete."""

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return request.user.is_superuser
