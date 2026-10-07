"""项目根 URL 配置。"""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # Web 页面
    path("", include("requirements.urls_web")),
    # REST API
    path("api/", include("requirements.urls_api")),
]
