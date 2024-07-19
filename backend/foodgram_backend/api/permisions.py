from rest_framework.permissions import BasePermission


class IsAuthorOrAdmin(BasePermission):
    def has_permission(self, request, view):
        if request.method == 'POST':
            return request.user and (
                request.user.is_staff
                or request.user.is_authenticated
            )
        return True

    def has_object_permission(self, request, view, obj):
        if request.method in ['PUT', 'PATCH', 'DELETE']:
            return request.user and (
                request.user.is_staff
                or obj.author == request.user
            )
        return True
