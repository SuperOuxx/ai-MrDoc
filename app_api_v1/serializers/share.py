from rest_framework import serializers

from app_doc.models import DocShare


class DocShareSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocShare
        fields = ["id", "token", "share_type", "share_value", "is_enable", "create_time"]
        read_only_fields = ["id", "create_time"]
