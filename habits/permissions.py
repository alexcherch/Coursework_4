from rest_framework.permissions import BasePermission


class IsOwner(BasePermission):
    """Allow access only to the user who owns the object."""

    message = "You can only access your own habits."

    def has_object_permission(self, request, view, obj):
        return obj.user_id == request.user.id
