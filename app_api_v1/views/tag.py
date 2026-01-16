from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from app_api_v1.serializers.tag import TagSerializer
from app_api_v1.utils.responses import api_response
from app_doc.models import Tag, DocTag, Doc


class TagViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = TagSerializer
    queryset = Tag.objects.all().order_by("name")

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.query_params.get("q")
        if q:
            qs = qs.filter(name__icontains=q)
        return qs

    @action(detail=True, methods=["get"])
    def docs(self, request, pk=None):
        tag = self.get_object()
        doc_ids = DocTag.objects.filter(tag=tag, doc__status__lt=3).values_list("doc_id", flat=True)
        docs = Doc.objects.filter(id__in=doc_ids)
        data = [
            {"id": d.id, "name": d.name, "top_doc": d.top_doc, "parent_doc": d.parent_doc, "status": d.status}
            for d in docs
        ]
        return api_response(data=data, msg="ok")
