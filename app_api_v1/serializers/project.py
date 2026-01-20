from rest_framework import serializers

from app_doc.models import Doc, Project, ProjectCollaborator


class ProjectSerializer(serializers.ModelSerializer):
    doc_count = serializers.SerializerMethodField()
    collaborator_count = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            "id",
            "name",
            "icon",
            "intro",
            "index_position",
            "role",
            "role_value",
            "is_watermark",
            "watermark_type",
            "watermark_value",
            "is_top",
            "create_user",
            "create_time",
            "modify_time",
            "doc_count",
            "collaborator_count",
        ]
        read_only_fields = ("id", "create_user", "create_time", "modify_time", "doc_count", "collaborator_count")

    def get_doc_count(self, obj: Project) -> int:
        return Doc.objects.filter(top_doc=obj.id).count()

    def get_collaborator_count(self, obj: Project) -> int:
        return ProjectCollaborator.objects.filter(project=obj).count()


class ProjectCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = [
            "name",
            "icon",
            "intro",
            "index_position",
            "role",
            "role_value",
            "is_watermark",
            "watermark_type",
            "watermark_value",
            "is_top",
        ]

    def create(self, validated_data):
        request = self.context["request"]
        validated_data["create_user"] = request.user
        return super().create(validated_data)
