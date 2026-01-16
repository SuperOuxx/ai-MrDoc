from typing import Optional

from django.contrib.auth import get_user_model

from app_doc.models import Doc, Project, ProjectCollaborator
from .base import Action, BasePolicy
from .project_policy import ProjectAccessPolicy


User = get_user_model()


class DocAccessPolicy(BasePolicy):
    """Document-level permission checks with collaborator role differences."""

    @staticmethod
    def get_doc_project(doc: Doc) -> Optional[Project]:
        try:
            return Project.objects.get(id=doc.top_doc)
        except Project.DoesNotExist:
            return None

    @staticmethod
    def is_draft(doc: Doc) -> bool:
        return doc.status == 0

    @staticmethod
    def has_read_permission(user, doc: Doc, viewcode: str = None) -> bool:
        # superuser
        if DocAccessPolicy.is_superuser(user):
            return True

        # draft: only creator
        if DocAccessPolicy.is_draft(doc):
            return DocAccessPolicy.is_creator(user, doc)

        project = DocAccessPolicy.get_doc_project(doc)
        if not project:
            return False
        return ProjectAccessPolicy.has_read_permission(user, project, viewcode)

    @staticmethod
    def has_create_permission(user, project: Project) -> bool:
        if not DocAccessPolicy.is_authenticated(user):
            return False
        if DocAccessPolicy.is_superuser(user):
            return True
        if DocAccessPolicy.is_creator(user, project):
            return True
        if ProjectAccessPolicy.is_collaborator(user, project):
            return True
        return False

    @staticmethod
    def has_update_permission(user, doc: Doc) -> bool:
        if not DocAccessPolicy.is_authenticated(user):
            return False
        if DocAccessPolicy.is_superuser(user):
            return True

        project = DocAccessPolicy.get_doc_project(doc)
        if not project:
            return False

        if DocAccessPolicy.is_creator(user, project):
            return True
        if DocAccessPolicy.is_creator(user, doc):
            return True

        colla_role = ProjectAccessPolicy.get_collaborator_role(user, project)
        if colla_role is not None:
            if colla_role == 1:
                return True
            if colla_role == 0:
                return DocAccessPolicy.is_creator(user, doc)
        return False

    @staticmethod
    def has_delete_permission(user, doc: Doc) -> bool:
        if not DocAccessPolicy.is_authenticated(user):
            return False
        if DocAccessPolicy.is_superuser(user):
            return True

        project = DocAccessPolicy.get_doc_project(doc)
        if not project:
            return False

        if DocAccessPolicy.is_creator(user, project):
            return True

        colla_role = ProjectAccessPolicy.get_collaborator_role(user, project)
        if colla_role is not None:
            if colla_role == 1:
                return True  # role=1 collaborator can delete any doc
            if colla_role == 0:
                return DocAccessPolicy.is_creator(user, doc)

        if DocAccessPolicy.is_creator(user, doc):
            return True

        return False

    @staticmethod
    def can_perform_action(user, doc: Doc, action: Action, viewcode: str = None) -> bool:
        if action == Action.VIEW:
            return DocAccessPolicy.has_read_permission(user, doc, viewcode)
        if action == Action.UPDATE:
            return DocAccessPolicy.has_update_permission(user, doc)
        if action == Action.DELETE:
            return DocAccessPolicy.has_delete_permission(user, doc)
        if action == Action.CREATE:
            project = DocAccessPolicy.get_doc_project(doc)
            return DocAccessPolicy.has_create_permission(user, project) if project else False
        return False
