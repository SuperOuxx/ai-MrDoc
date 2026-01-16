from rest_framework import serializers

from app_doc.models import Doc


class DocSerializer(serializers.ModelSerializer):
    class Meta:
        model = Doc
        fields = [
            "id",
            "name",
            "pre_content",
            "content",
            "parent_doc",
            "top_doc",
            "sort",
            "create_user",
            "create_time",
            "modify_time",
            "status",
            "editor_mode",
            "open_children",
            "show_children",
        ]
        read_only_fields = ("id", "create_user", "create_time", "modify_time")


class DocCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Doc
        fields = [
            "name",
            "pre_content",
            "content",
            "parent_doc",
            "top_doc",
            "sort",
            "status",
            "editor_mode",
            "open_children",
            "show_children",
        ]

    def create(self, validated_data):
        request = self.context["request"]
        validated_data["create_user"] = request.user
        return super().create(validated_data)
