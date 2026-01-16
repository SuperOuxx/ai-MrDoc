from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from app_api_v1.serializers.auth import ApiTokenObtainPairSerializer, UserBriefSerializer
from app_api_v1.utils.responses import api_response
from app_api_v1.utils.versioning import add_api_version_header

User = get_user_model()


class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class = ApiTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except (ValidationError, InvalidToken, TokenError) as exc:
            detail = getattr(exc, "detail", None) or {"detail": str(exc)}
            return api_response(
                data=detail,
                msg="Invalid credentials or token",
                code=1,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        return api_response(data=serializer.validated_data, msg="ok")


class RefreshView(TokenRefreshView):
    permission_classes = [AllowAny]
    serializer_class = TokenRefreshSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except (ValidationError, InvalidToken, TokenError) as exc:
            detail = getattr(exc, "detail", None) or {"detail": str(exc)}
            return api_response(
                data=detail,
                msg="Invalid refresh token",
                code=1,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        return api_response(data=serializer.validated_data, msg="ok")


class UserMeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user_data = UserBriefSerializer(request.user).data
        return api_response(data=user_data, msg="ok")


class ApiSchemaView(SpectacularAPIView):
    """OpenAPI schema with version header."""

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        return add_api_version_header(response)


class ApiSwaggerView(SpectacularSwaggerView):
    """Swagger UI with version header."""

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        return add_api_version_header(response)
