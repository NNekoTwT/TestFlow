"""Web 页面路由。"""
from django.urls import path

from . import views_web

urlpatterns = [
    path("", views_web.dashboard, name="dashboard"),
    path("requirements/", views_web.requirement_list, name="requirement_list"),
    path("requirements/new/", views_web.requirement_create, name="requirement_create"),
    path("requirements/<int:pk>/", views_web.requirement_detail, name="requirement_detail"),
]
