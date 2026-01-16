from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from app_api_v1.policies.doc_policy import DocAccessPolicy
from app_api_v1.policies.project_policy import ProjectAccessPolicy
from app_doc.models import Doc, Project, ProjectCollaborator, DocHistory
from app_api_v1.views.doc import DocViewSet


User = get_user_model()


class PermissionSmokeTests(TestCase):
    """Focused smoke tests to guard collaborator delete semantics (role=1 can delete any doc)."""

    def setUp(self):
        self.creator = User.objects.create_user(username="creator", password="x")
        self.collab_all = User.objects.create_user(username="colla_all", password="x")
        self.collab_self = User.objects.create_user(username="colla_self", password="x")
        self.other = User.objects.create_user(username="other", password="x")
        self.project = Project.objects.create(name="P1", intro="i", role=1, create_user=self.creator)
        ProjectCollaborator.objects.create(project=self.project, user=self.collab_all, role=1)
        ProjectCollaborator.objects.create(project=self.project, user=self.collab_self, role=0)
        self.doc_by_creator = Doc.objects.create(name="d1", pre_content="", content="", top_doc=self.project.id, create_user=self.creator, status=1)
        self.doc_by_other = Doc.objects.create(name="d2", pre_content="", content="", top_doc=self.project.id, create_user=self.other, status=1)

    def test_role1_collaborator_can_delete_any_doc(self):
        assert ProjectAccessPolicy.get_collaborator_role(self.collab_all, self.project) == 1
        assert DocAccessPolicy.has_delete_permission(self.collab_all, self.doc_by_creator) is True
        assert DocAccessPolicy.has_delete_permission(self.collab_all, self.doc_by_other) is True

    def test_role0_collaborator_can_delete_only_own(self):
        assert ProjectAccessPolicy.get_collaborator_role(self.collab_self, self.project) == 0
        assert DocAccessPolicy.has_delete_permission(self.collab_self, self.doc_by_self()) is True
        assert DocAccessPolicy.has_delete_permission(self.collab_self, self.doc_by_other) is False

    def doc_by_self(self):
        return Doc.objects.create(
            name="d3",
            pre_content="",
            content="",
            top_doc=self.project.id,
            create_user=self.collab_self,
            status=1,
        )


class DocCrudTests(TestCase):
    """Doc CRUD behaviors: history on update, soft delete."""

    def setUp(self):
        self.creator = User.objects.create_user(username="creator2", password="x")
        self.project = Project.objects.create(name="P2", intro="i", role=1, create_user=self.creator)
        self.doc = Doc.objects.create(
            name="doc",
            pre_content="old",
            content="old",
            top_doc=self.project.id,
            create_user=self.creator,
            status=1,
        )
        self.factory = APIRequestFactory()

    def test_update_creates_history(self):
        view = DocViewSet.as_view({"put": "update"})
        payload = {
            "name": "doc",
            "pre_content": "new",
            "content": "new",
            "parent_doc": 0,
            "top_doc": self.project.id,
            "sort": 1,
            "status": 1,
            "editor_mode": 1,
            "open_children": False,
            "show_children": False,
        }
        request = self.factory.put(f"/api/v1/docs/{self.doc.id}/", payload, format="json")
        force_authenticate(request, user=self.creator)
        response = view(request, pk=self.doc.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(DocHistory.objects.filter(doc=self.doc).count(), 1)

    def test_soft_delete_sets_status(self):
        view = DocViewSet.as_view({"delete": "destroy"})
        request = self.factory.delete(f"/api/v1/docs/{self.doc.id}/")
        force_authenticate(request, user=self.creator)
        response = view(request, pk=self.doc.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Doc.objects.get(id=self.doc.id).status, 3)
