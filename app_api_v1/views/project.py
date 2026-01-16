from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from app_api_v1.permissions.project import ProjectManagePermission, ProjectPermission
from app_api_v1.permissions.utils import get_user_manageable_projects, get_user_readable_projects, get_user_writable_projects
from app_api_v1.serializers.doc import DocSerializer
from app_api_v1.serializers.project import ProjectCreateUpdateSerializer, ProjectSerializer
from app_api_v1.utils.pagination import ApiPageNumberPagination
from app_api_v1.utils.responses import api_response
from app_doc.models import Project, ProjectCollaborator, Doc, ProjectToc
from django.db import transaction


class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    permission_classes = [ProjectPermission]
    serializer_class = ProjectSerializer
    pagination_class = ApiPageNumberPagination

    def get_queryset(self):
        user = self.request.user
        readable_ids = get_user_readable_projects(user)
        return self.queryset.filter(id__in=readable_ids).order_by("-modify_time")

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return ProjectCreateUpdateSerializer
        return ProjectSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return api_response(data=serializer.data, msg="ok")

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return api_response(data=serializer.data, msg="ok")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        read_serializer = ProjectSerializer(serializer.instance, context=self.get_serializer_context())
        return api_response(data=read_serializer.data, msg="created")

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        read_serializer = ProjectSerializer(instance, context=self.get_serializer_context())
        return api_response(data=read_serializer.data, msg="updated")

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return api_response(data=None, msg="deleted")

    @action(
        detail=True,
        methods=["get"],
        permission_classes=[ProjectPermission],
    )
    def collaborators(self, request, pk=None):
        project = self.get_object()
        collas = ProjectCollaborator.objects.filter(project=project).select_related("user")
        data = [
            {
                "id": c.user_id,
                "username": c.user.username,
                "role": c.role,
            }
            for c in collas
        ]
        return api_response(data=data, msg="ok")

    @action(
        detail=True,
        methods=["get"],
        permission_classes=[ProjectPermission],
    )
    def docs(self, request, pk=None):
        project = self.get_object()
        docs = Doc.objects.filter(top_doc=project.id, status__lt=3)
        q = request.query_params.get("q")
        if q:
            docs = docs.filter(name__icontains=q)
        docs = docs.order_by("sort", "-modify_time")
        serializer = DocSerializer(docs, many=True)
        return api_response(data=serializer.data, msg="ok")

    @action(
        detail=True,
        methods=["get"],
        permission_classes=[ProjectPermission],
    )
    def tree(self, request, pk=None):
        project = self.get_object()
        toc = ProjectToc.objects.filter(project=project).first()
        if toc and toc.value:
            try:
                import json
                tree_data = json.loads(toc.value)
                return api_response(data=tree_data, msg="ok")
            except Exception:
                pass

        # fallback: build simple tree from docs
        docs = list(Doc.objects.filter(top_doc=project.id, status__lt=3).values("id", "name", "parent_doc", "sort"))
        by_parent = {}
        for d in docs:
            by_parent.setdefault(d["parent_doc"], []).append(d)
        for children in by_parent.values():
            children.sort(key=lambda x: (x["sort"], x["id"]))

        def build(parent_id):
            result = []
            for d in by_parent.get(parent_id, []):
                result.append(
                    {
                        "id": d["id"],
                        "name": d["name"],
                        "children": build(d["id"]),
                    }
                )
            return result

        tree = build(0)
        return api_response(data=tree, msg="ok")

    @tree.mapping.put
    def update_tree(self, request, pk=None):
        project = self.get_object()
        tree_data = request.data.get("tree") or []
        if not isinstance(tree_data, list):
            return api_response(data=None, msg="tree must be a list", code=1, status_code=400)

        updates = []

        def walk(nodes, parent_id):
            for idx, node in enumerate(nodes):
                node_id = node.get("id")
                if not node_id:
                    continue
                updates.append((node_id, parent_id, idx))
                children = node.get("children") or []
                walk(children, node_id)

        walk(tree_data, 0)

        with transaction.atomic():
            for doc_id, parent_id, sort in updates:
                Doc.objects.filter(id=doc_id, top_doc=project.id).update(parent_doc=parent_id, sort=sort)
            # store toc
            ProjectToc.objects.update_or_create(project=project, defaults={"value": request.data.get("tree")})
        return api_response(data=None, msg="tree updated")
