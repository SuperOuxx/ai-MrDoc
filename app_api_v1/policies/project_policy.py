from typing import Optional

from django.contrib.auth import get_user_model

from app_doc.models import Project, ProjectCollaborator
from .base import Action, BasePolicy


User = get_user_model()


class ProjectAccessPolicy(BasePolicy):
    """Project-level permission checks aligned with legacy rules."""

    @staticmethod
    def is_collaborator(user, project: Project) -> bool:
        if not BasePolicy.is_authenticated(user):
            return False
        return ProjectCollaborator.objects.filter(project=project, user=user).exists()

    @staticmethod
    def get_collaborator_role(user, project: Project) -> Optional[int]:
        if not BasePolicy.is_authenticated(user):
            return None
        colla = ProjectCollaborator.objects.filter(project=project, user=user).first()
        return colla.role if colla else None

    @staticmethod
    def is_role2_permitted_user(user, project: Project) -> bool:
        if not BasePolicy.is_authenticated(user):
            return False
        if project.role != 2 or not project.role_value:
            return False
        return str(user.username) in project.role_value

    @staticmethod
    def has_read_permission(user, project: Project, viewcode: str = None) -> bool:
        # superuser
        if ProjectAccessPolicy.is_superuser(user):
            return True
        # creator
        if ProjectAccessPolicy.is_creator(user, project):
            return True
        # collaborator
        if ProjectAccessPolicy.is_collaborator(user, project):
            return True

        # role-based visibility
        if project.role == 0:
            return True
        if project.role == 1:
            return False
        if project.role == 2:
            return ProjectAccessPolicy.is_role2_permitted_user(user, project)
        if project.role == 3:
            return bool(viewcode) and project.role_value == viewcode
        return False

    @staticmethod
    def has_write_permission(user, project: Project) -> bool:
        if not ProjectAccessPolicy.is_authenticated(user):
            return False
        if ProjectAccessPolicy.is_superuser(user):
            return True
        if ProjectAccessPolicy.is_creator(user, project):
            return True
        if ProjectAccessPolicy.is_collaborator(user, project):
            return True
        return False

    @staticmethod
    def has_manage_permission(user, project: Project) -> bool:
        if not ProjectAccessPolicy.is_authenticated(user):
            return False
        if ProjectAccessPolicy.is_superuser(user):
            return True
        if ProjectAccessPolicy.is_creator(user, project):
            return True
        return False

    @staticmethod
    def can_perform_action(user, project: Project, action: Action, viewcode: str = None) -> bool:
        if action == Action.VIEW:
            return ProjectAccessPolicy.has_read_permission(user, project, viewcode)
        if action in {Action.CREATE, Action.UPDATE, Action.DELETE}:
            return ProjectAccessPolicy.has_write_permission(user, project)
        if action == Action.MANAGE:
            return ProjectAccessPolicy.has_manage_permission(user, project)
        return False
