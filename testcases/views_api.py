"""测试用例相关 API：生成、列表、评审、相似检索、导出。"""
from urllib.parse import quote

from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView

from core.exceptions import BadRequestError, NotFoundError
from core.exports import export_excel, export_markdown
from core.responses import ok
from requirements.models import Requirement

from .models import TestCase, TestPoint
from .serializers import GenerationRecordSerializer, TestCaseSerializer, TestPointSerializer
from .services import GenerationService


def _get_requirement(pk):
    try:
        return Requirement.objects.get(pk=pk)
    except Requirement.DoesNotExist:
        raise NotFoundError("需求不存在")


@method_decorator(csrf_exempt, name="dispatch")
class GenerateView(APIView):
    """POST 触发 AI 测试用例生成。"""

    def post(self, request, pk):
        requirement = _get_requirement(pk)
        record = GenerationService().generate(requirement)
        return ok(
            {
                "generation": GenerationRecordSerializer(record).data,
                "test_case_count": requirement.test_cases.count(),
                "test_point_count": requirement.test_points.count(),
            },
            message="生成完成",
        )


class TestCaseListView(APIView):
    """GET 某需求的测试用例列表，支持类型 / 优先级 / 设计方法筛选。"""

    def get(self, request, pk):
        requirement = _get_requirement(pk)
        qs = requirement.test_cases.all()

        test_type = request.query_params.get("test_type")
        priority = request.query_params.get("priority")
        design_method = request.query_params.get("design_method")

        if test_type:
            qs = qs.filter(test_type=test_type)
        if priority:
            qs = qs.filter(priority=priority)
        if design_method:
            qs = qs.filter(design_method=design_method)

        return ok(TestCaseSerializer(qs, many=True).data)


@method_decorator(csrf_exempt, name="dispatch")
class TestPointListView(APIView):
    """GET 列表 / POST 新增测试点。"""

    def get(self, request, pk):
        requirement = _get_requirement(pk)
        return ok(TestPointSerializer(requirement.test_points.all(), many=True).data)

    def post(self, request, pk):
        requirement = _get_requirement(pk)
        serializer = TestPointSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(requirement=requirement)
        return ok(serializer.data, message="测试点已新增")


@method_decorator(csrf_exempt, name="dispatch")
class TestPointGenerateView(APIView):
    """POST 只生成测试点（不生成测试用例）。"""

    def post(self, request, pk):
        requirement = _get_requirement(pk)
        points = GenerationService().generate_test_points(requirement)
        return ok(
            TestPointSerializer(points, many=True).data,
            message=f"已生成 {len(points)} 个测试点",
        )


@method_decorator(csrf_exempt, name="dispatch")
class TestPointDetailView(APIView):
    """PATCH 编辑 / 勾选单个测试点；DELETE 删除单个测试点。"""

    def get_object(self, pk, tp_id):
        try:
            return TestPoint.objects.get(pk=tp_id, requirement_id=pk)
        except TestPoint.DoesNotExist:
            raise NotFoundError("测试点不存在")

    def patch(self, request, pk, tp_id):
        instance = self.get_object(pk, tp_id)
        serializer = TestPointSerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return ok(serializer.data, message="测试点已更新")

    def delete(self, request, pk, tp_id):
        self.get_object(pk, tp_id).delete()
        return ok(message="测试点已删除")


@method_decorator(csrf_exempt, name="dispatch")
class TestPointBatchSelectView(APIView):
    """POST 批量设置选中状态（用于全选 / 取消全选）。body: {"selected": true}"""

    def post(self, request, pk):
        requirement = _get_requirement(pk)
        selected = request.data.get("selected")
        if not isinstance(selected, bool):
            raise BadRequestError("selected 必须是布尔值")
        requirement.test_points.update(selected=selected)
        return ok(message="全选" if selected else "取消全选")


@method_decorator(csrf_exempt, name="dispatch")
class TestCaseGenerateFromPointsView(APIView):
    """POST 根据选中的测试点生成测试用例。body: {"test_point_ids": [1,2,3]}（可省略，省略则用全部已选）"""

    def post(self, request, pk):
        requirement = _get_requirement(pk)
        ids = request.data.get("test_point_ids")
        if ids is None:
            ids = list(
                requirement.test_points.filter(selected=True).values_list("id", flat=True)
            )
        else:
            try:
                ids = [int(i) for i in ids]
            except (TypeError, ValueError):
                raise BadRequestError("test_point_ids 必须是整数数组")

        record = GenerationService().generate_from_test_points(requirement, ids)
        return ok(
            {
                "generation": GenerationRecordSerializer(record).data,
                "test_case_count": requirement.test_cases.count(),
            },
            message="测试用例生成完成",
        )


class ReviewView(APIView):
    """GET 最新一次生成的质量检查结果。"""

    def get(self, request, pk):
        requirement = _get_requirement(pk)
        record = (
            requirement.generation_records.filter(status="success")
            .exclude(review_result__isnull=True)
            .first()
        )
        if record is None:
            raise NotFoundError("暂无评审结果，请先生成测试用例")
        return ok(record.review_result)


class SimilarView(APIView):
    """GET 相似历史用例（向量语义检索）。"""

    def get(self, request, pk):
        requirement = _get_requirement(pk)
        cases = GenerationService().find_similar_cases(requirement)
        return ok(TestCaseSerializer(cases, many=True).data)


class ExportExcelView(APIView):
    """GET 导出测试用例为 Excel。"""

    def get(self, request, pk):
        requirement = _get_requirement(pk)
        test_cases = list(requirement.test_cases.all())
        if not test_cases:
            raise NotFoundError("暂无测试用例可导出")
        content = export_excel(test_cases)
        filename = quote(f"{requirement.title}_测试用例.xlsx")
        response = HttpResponse(
            content,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f"attachment; filename*=UTF-8''{filename}"
        return response


class ExportMarkdownView(APIView):
    """GET 导出测试用例为 Markdown。"""

    def get(self, request, pk):
        requirement = _get_requirement(pk)
        test_cases = list(requirement.test_cases.all())
        if not test_cases:
            raise NotFoundError("暂无测试用例可导出")
        content = export_markdown(requirement, test_cases)
        filename = quote(f"{requirement.title}_测试用例.md")
        response = HttpResponse(content, content_type="text/markdown; charset=utf-8")
        response["Content-Disposition"] = f"attachment; filename*=UTF-8''{filename}"
        return response
