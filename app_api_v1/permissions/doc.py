from rest_framework import permissions

from app_api_v1.policies.doc_policy import DocAccessPolicy
from app_api_v1.policies.project_policy import ProjectAccessPolicy
from app_doc.models import Project


class DocPermission(permissions.BasePermission):
    """Document permissions mapped to DRF lifecycle."""

    message = "您没有权限访问该文档"

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True

        if request.method == "POST":
            if not (request.user and request.user.is_authenticated):
                return False
            project_id = request.data.get("top_doc") or request.data.get("project_id")
            if not project_id:
                return False
            try:
                project = Project.objects.get(id=project_id)
            except Project.DoesNotExist:
                return False
            return DocAccessPolicy.has_create_permission(request.user, project)
        return True

    def has_object_permission(self, request, view, obj):
        project = DocAccessPolicy.get_doc_project(obj)
        viewcode = request.COOKIES.get(f"viewcode-{project.id}") if project else None

        if request.method in permissions.SAFE_METHODS:
            return DocAccessPolicy.has_read_permission(request.user, obj, viewcode)

        if request.method in ["PUT", "PATCH"]:
            return DocAccessPolicy.has_update_permission(request.user, obj)

        if request.method == "DELETE":
            return DocAccessPolicy.has_delete_permission(request.user, obj)

        return False
