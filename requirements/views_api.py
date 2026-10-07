"""需求管理 API。

说明：本项目为无鉴权演示，为方便 curl / 前端直接调用，
对 API 视图统一关闭 CSRF（Web 表单仍走带 CSRF 的 Django 视图）。
"""
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView

from core.exceptions import NotFoundError
from core.responses import ok

from .models import Requirement
from .serializers import RequirementSerializer


@method_decorator(csrf_exempt, name="dispatch")
class RequirementListCreateView(APIView):
    """GET 列表 / POST 创建。"""

    def get(self, request):
        qs = Requirement.objects.all()
        module = request.query_params.get("module")
        if module:
            qs = qs.filter(module__icontains=module)
        return ok(RequirementSerializer(qs, many=True).data)

    def post(self, request):
        serializer = RequirementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return ok(serializer.data, message="创建成功")


@method_decorator(csrf_exempt, name="dispatch")
class RequirementDetailView(APIView):
    """GET 详情 / PUT 更新 / DELETE 删除。"""

    def get_object(self, pk):
        try:
            return Requirement.objects.get(pk=pk)
        except Requirement.DoesNotExist:
            raise NotFoundError("需求不存在")

    def get(self, request, pk):
        return ok(RequirementSerializer(self.get_object(pk)).data)

    def put(self, request, pk):
        instance = self.get_object(pk)
        serializer = RequirementSerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return ok(serializer.data, message="更新成功")

    def delete(self, request, pk):
        self.get_object(pk).delete()
        return ok(message="删除成功")
