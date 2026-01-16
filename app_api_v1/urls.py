from django.urls import path, re_path
from rest_framework.routers import DefaultRouter

from app_api_v1.views.auth import ApiSchemaView, ApiSwaggerView, LoginView, RefreshView, UserMeView
from app_api_v1.views.doc import DocViewSet
from app_api_v1.views.project import ProjectViewSet
from app_api_v1.views.tag import TagViewSet

router = DefaultRouter()
router.register("projects", ProjectViewSet, basename="api-v1-projects")
router.register("docs", DocViewSet, basename="api-v1-docs")
router.register("tags", TagViewSet, basename="api-v1-tags")

urlpatterns = [
    re_path(r"^auth/login/?$", LoginView.as_view(), name="api-v1-auth-login"),
    re_path(r"^auth/refresh/?$", RefreshView.as_view(), name="api-v1-auth-refresh"),
    re_path(r"^users/me/?$", UserMeView.as_view(), name="api-v1-users-me"),
    path("schema/", ApiSchemaView.as_view(), name="api-v1-schema"),
    path("docs/swagger/", ApiSwaggerView.as_view(url_name="api-v1-schema"), name="api-v1-docs"),
]

urlpatterns += router.urls
