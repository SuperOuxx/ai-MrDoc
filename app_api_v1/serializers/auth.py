from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


User = get_user_model()


class UserBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "is_superuser", "is_staff", "first_name", "last_name")


class ApiTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Return JWT pair with user info."""

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = UserBriefSerializer(self.user).data
        return data
