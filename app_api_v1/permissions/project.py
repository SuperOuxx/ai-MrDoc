from rest_framework import permissions

from app_api_v1.policies.project_policy import ProjectAccessPolicy


class ProjectPermission(permissions.BasePermission):
    """Project permissions mapped to DRF lifecycle."""

    message = "您没有权限访问该文集"

    def has_permission(self, request, view):
        # list/retrieve allowed; creation requires auth
        if request.method in permissions.SAFE_METHODS:
            return True
        if request.method == "POST":
            return bool(request.user and request.user.is_authenticated)
        return True

    def has_object_permission(self, request, view, obj):
        viewcode = request.COOKIES.get(f"viewcode-{obj.id}")

        if request.method in permissions.SAFE_METHODS:
            return ProjectAccessPolicy.has_read_permission(request.user, obj, viewcode)

        if request.method in ["PUT", "PATCH"]:
            # role updates require manage
            if "role" in request.data or "role_value" in request.data:
                return ProjectAccessPolicy.has_manage_permission(request.user, obj)
            return ProjectAccessPolicy.has_write_permission(request.user, obj)

        if request.method == "DELETE":
            return ProjectAccessPolicy.has_manage_permission(request.user, obj)

        return False


class ProjectManagePermission(permissions.BasePermission):
    """Management endpoints (collaborators/permissions)."""

    message = "您没有权限管理该文集"

    def has_object_permission(self, request, view, obj):
        return ProjectAccessPolicy.has_manage_permission(request.user, obj)
