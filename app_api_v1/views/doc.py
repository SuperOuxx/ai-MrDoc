from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework import status
from django.db import transaction

from app_api_v1.permissions.doc import DocPermission
from app_api_v1.permissions.utils import get_user_readable_projects
from app_api_v1.serializers.doc import DocCreateUpdateSerializer, DocSerializer
from app_api_v1.utils.pagination import ApiPageNumberPagination
from app_api_v1.utils.responses import api_response
from app_doc.models import Doc, DocHistory, DocTag, Tag, DocShare
from app_api_v1.policies.doc_policy import DocAccessPolicy
from app_api_v1.serializers.share import DocShareSerializer


class DocViewSet(viewsets.ModelViewSet):
    queryset = Doc.objects.all()
    permission_classes = [DocPermission]
    serializer_class = DocSerializer
    pagination_class = ApiPageNumberPagination

    def get_queryset(self):
        user = self.request.user
        readable_ids = get_user_readable_projects(user)
        qs = self.queryset.filter(top_doc__in=readable_ids)
        top_doc = self.request.query_params.get("top_doc")
        if top_doc:
            qs = qs.filter(top_doc=top_doc)
        parent_doc = self.request.query_params.get("parent_doc")
        if parent_doc:
            qs = qs.filter(parent_doc=parent_doc)
        q = self.request.query_params.get("q")
        if q:
            qs = qs.filter(name__icontains=q)
        return qs.order_by("-modify_time")

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return DocCreateUpdateSerializer
        return DocSerializer

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
        read_serializer = DocSerializer(serializer.instance, context=self.get_serializer_context())
        return api_response(data=read_serializer.data, msg="created")

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        # capture history before update
        DocHistory.objects.create(doc=instance, pre_content=instance.pre_content, create_user=request.user)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        read_serializer = DocSerializer(instance, context=self.get_serializer_context())
        return api_response(data=read_serializer.data, msg="updated")

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        # soft delete: align with legacy behavior (status=3)
        instance.status = 3
        instance.save(update_fields=["status"])
        # cascade children soft delete
        Doc.objects.filter(parent_doc=instance.id).update(status=3)
        return api_response(data=None, msg="deleted")

    @action(detail=True, methods=["get", "post"], permission_classes=[DocPermission])
    def tags(self, request, pk=None):
        doc = self.get_object()
        if request.method.lower() == "get":
            tags = DocTag.objects.filter(doc=doc).select_related("tag")
            data = [{"id": t.tag.id, "name": t.tag.name} for t in tags]
            return api_response(data=data, msg="ok")

        # POST: replace tags (requires update permission)
        if not DocAccessPolicy.has_update_permission(request.user, doc):
            return api_response(data=None, msg="无权限", code=1, status_code=status.HTTP_403_FORBIDDEN)
        names = request.data.get("tags") or []
        if not isinstance(names, list):
            return api_response(data=None, msg="tags must be list", code=1, status_code=status.HTTP_400_BAD_REQUEST)
        cleaned = [str(n).strip() for n in names if str(n).strip()]
        with transaction.atomic():
            existing = set()
            for name in cleaned:
                tag, _ = Tag.objects.get_or_create(name=name, defaults={"create_user": request.user})
                DocTag.objects.get_or_create(tag=tag, doc=doc)
                existing.add(tag.id)

            DocTag.objects.filter(doc=doc).exclude(tag_id__in=existing).delete()
            tags = DocTag.objects.filter(doc=doc).select_related("tag")
            data = [{"id": t.tag.id, "name": t.tag.name} for t in tags]
        return api_response(data=data, msg="updated")

    @action(detail=True, methods=["get", "post"], permission_classes=[DocPermission])
    def share(self, request, pk=None):
        doc = self.get_object()
        if request.method.lower() == "get":
            share = DocShare.objects.filter(doc=doc).first()
            if not share:
                return api_response(data=None, msg="未创建分享")
            return api_response(data=DocShareSerializer(share).data, msg="ok")

        # POST to create/update share
        if not DocAccessPolicy.has_update_permission(request.user, doc):
            return api_response(data=None, msg="无权限", code=1, status_code=status.HTTP_403_FORBIDDEN)

        payload = {
            "share_type": request.data.get("share_type", 0),
            "share_value": request.data.get("share_value"),
            "is_enable": request.data.get("is_enable", True),
        }
        share, _ = DocShare.objects.update_or_create(doc=doc, defaults=payload)
        serializer = DocShareSerializer(share)
        return api_response(data=serializer.data, msg="updated")
