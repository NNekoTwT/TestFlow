"""API 路由。

需求 CRUD 由本应用提供；生成 / 用例 / 评审 / 相似 / 导出等子资源
由 testcases 应用提供，但统一挂在 /api/requirements/<id>/ 下。
"""
from django.urls import path

from testcases import views_api as testcase_views

from . import views_api

urlpatterns = [
    path("requirements/", views_api.RequirementListCreateView.as_view(), name="api_requirement_list"),
    path("requirements/<int:pk>/", views_api.RequirementDetailView.as_view(), name="api_requirement_detail"),
    # 子资源
    path("requirements/<int:pk>/generate/", testcase_views.GenerateView.as_view(), name="api_generate"),
    path("requirements/<int:pk>/testcases/", testcase_views.TestCaseListView.as_view(), name="api_testcases"),
    path("requirements/<int:pk>/testcases/generate/", testcase_views.TestCaseGenerateFromPointsView.as_view(), name="api_testcase_generate_from_points"),
    path("requirements/<int:pk>/testpoints/", testcase_views.TestPointListView.as_view(), name="api_testpoints"),
    path("requirements/<int:pk>/testpoints/generate/", testcase_views.TestPointGenerateView.as_view(), name="api_testpoint_generate"),
    path("requirements/<int:pk>/testpoints/select/", testcase_views.TestPointBatchSelectView.as_view(), name="api_testpoint_select"),
    path("requirements/<int:pk>/testpoints/<int:tp_id>/", testcase_views.TestPointDetailView.as_view(), name="api_testpoint_detail"),
    path("requirements/<int:pk>/review/", testcase_views.ReviewView.as_view(), name="api_review"),
    path("requirements/<int:pk>/similar/", testcase_views.SimilarView.as_view(), name="api_similar"),
    path("requirements/<int:pk>/export/excel/", testcase_views.ExportExcelView.as_view(), name="api_export_excel"),
    path("requirements/<int:pk>/export/markdown/", testcase_views.ExportMarkdownView.as_view(), name="api_export_markdown"),
]
