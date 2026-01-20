from typing import List

from django.contrib.auth import get_user_model

from app_doc.models import Project, ProjectCollaborator

User = get_user_model()


def get_user_readable_projects(user) -> List[int]:
    if not user or not getattr(user, "is_authenticated", False):
        return list(Project.objects.filter(role__in=[0, 3]).values_list("id", flat=True))

    if getattr(user, "is_superuser", False):
        return list(Project.objects.values_list("id", flat=True))

    colla_ids = list(
        ProjectCollaborator.objects.filter(user=user).values_list("project_id", flat=True)
    )
    own_ids = list(Project.objects.filter(create_user=user).values_list("id", flat=True))
    public_ids = list(Project.objects.filter(role__in=[0, 3]).values_list("id", flat=True))
    role2_ids = list(
        Project.objects.filter(role=2, role_value__contains=str(user.username)).values_list("id", flat=True)
    )

    return list(set(colla_ids) | set(own_ids) | set(public_ids) | set(role2_ids))


def get_user_writable_projects(user) -> List[int]:
    if not user or not getattr(user, "is_authenticated", False):
        return []
    if getattr(user, "is_superuser", False):
        return list(Project.objects.values_list("id", flat=True))
    colla_ids = list(
        ProjectCollaborator.objects.filter(user=user).values_list("project_id", flat=True)
    )
    own_ids = list(Project.objects.filter(create_user=user).values_list("id", flat=True))
    return list(set(colla_ids) | set(own_ids))


def get_user_manageable_projects(user) -> List[int]:
    if not user or not getattr(user, "is_authenticated", False):
        return []
    if getattr(user, "is_superuser", False):
        return list(Project.objects.values_list("id", flat=True))
    return list(Project.objects.filter(create_user=user).values_list("id", flat=True))
