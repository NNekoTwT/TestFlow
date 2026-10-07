"""Web 页面视图（Django Template 渲染）。"""
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from testcases.models import GenerationRecord, TestCase

from .models import Requirement


def dashboard(request):
    """首页 / Dashboard。"""
    context = {
        "requirement_count": Requirement.objects.count(),
        "testcase_count": TestCase.objects.count(),
        "generation_count": GenerationRecord.objects.count(),
    }
    return render(request, "dashboard.html", context)


def requirement_list(request):
    """需求历史列表。"""
    requirements = Requirement.objects.all().order_by("-created_at")
    return render(request, "requirements/requirement_list.html", {"requirements": requirements})


def requirement_create(request):
    """新建需求（HTML 表单）。"""
    context = {"form": {}}
    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        module = request.POST.get("module", "").strip()
        description = request.POST.get("description", "").strip()
        context["form"] = {"title": title, "module": module, "description": description}

        if not title or not description:
            context["error"] = "需求标题与描述不能为空"
            return render(request, "requirements/requirement_form.html", context)

        requirement = Requirement.objects.create(
            title=title, module=module, description=description
        )
        # 按所选入口决定详情页自动触发的生成模式：
        #   generate_cases  -> 直接生成测试用例（全流程）
        #   generate_points -> 先生成测试点（勾选后再生成用例）
        action = request.POST.get("action", "generate_cases")
        mode = "points" if action == "generate_points" else "cases"
        url = reverse("requirement_detail", kwargs={"pk": requirement.pk})
        return redirect(f"{url}?generate={mode}")

    return render(request, "requirements/requirement_form.html", context)


def requirement_detail(request, pk):
    """需求详情页（测试用例、质量检查、相似用例由前端调用 API 渲染）。"""
    requirement = get_object_or_404(Requirement, pk=pk)
    return render(request, "requirements/requirement_detail.html", {"requirement": requirement})
