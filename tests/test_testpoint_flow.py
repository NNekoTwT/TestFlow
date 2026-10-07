"""测试点独立流程测试：只生成测试点、按已选测试点生成用例、测试点 CRUD / 批量选择 API。"""
from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from ai.schemas.review import ReviewResult
from ai.schemas.testcase import TestCase as TestCaseSchema
from ai.schemas.testpoint import TestPoint as TestPointSchema
from core.exceptions import BadRequestError
from testcases.models import GenerationRecord, TestCase, TestPoint
from testcases.services import GenerationService


@pytest.fixture
def api_client():
    return APIClient()


def _points():
    return [
        TestPointSchema(title="正确手机号密码登录成功", description="", category="normal", priority="P0", design_method="scenario"),
        TestPointSchema(title="密码长度边界", description="8/20 位", category="boundary", priority="P1", design_method="boundary_value"),
    ]


def _cases():
    return [
        TestCaseSchema(
            case_id="TC_001", module="登录模块", title="登录成功",
            preconditions=[], steps=["输入手机号"], test_data="", expected_result="跳转首页",
            test_type="normal", priority="P0", design_method="scenario", test_point_index=0,
        ),
        TestCaseSchema(
            case_id="TC_002", module="登录模块", title="密码 7 位失败",
            preconditions=[], steps=["输入 7 位密码"], test_data="", expected_result="提示错误",
            test_type="boundary", priority="P1", design_method="boundary_value", test_point_index=1,
        ),
    ]


class FakePointsPipeline:
    def __init__(self, points):
        self.points = points

    def generate_test_points(self, title, module, description):
        return self.points


class FakeCaseGenerator:
    def __init__(self, cases):
        self.cases = cases

    def generate(self, module, description, test_points, similar_cases=None):
        return self.cases


class FakeReviewer:
    def review(self, description, test_cases):
        return ReviewResult()


class FakeTwoStagePipeline:
    def __init__(self, case_generator, reviewer):
        self.testcase_generator = case_generator
        self.reviewer = reviewer


@pytest.mark.django_db
class TestGenerateTestPointsService:
    def test_generate_test_points_persists(self, requirement):
        service = GenerationService(pipeline=FakePointsPipeline(_points()))
        saved = service.generate_test_points(requirement)

        assert len(saved) == 2
        assert TestPoint.objects.filter(requirement=requirement).count() == 2
        assert saved[0].title == "正确手机号密码登录成功"
        assert saved[0].priority == "P0"

    def test_generate_test_points_replaces(self, requirement):
        service = GenerationService(pipeline=FakePointsPipeline(_points()))
        service.generate_test_points(requirement)
        service.generate_test_points(requirement)
        assert TestPoint.objects.filter(requirement=requirement).count() == 2


@pytest.mark.django_db
class TestGenerateFromTestPointsService:
    def _make_requirement_with_points(self, requirement):
        tp1 = TestPoint.objects.create(requirement=requirement, title="点1", category="normal", priority="P0")
        tp2 = TestPoint.objects.create(requirement=requirement, title="点2", category="boundary", priority="P1")
        return tp1, tp2

    def test_generate_links_test_cases_to_points(self, requirement):
        tp1, tp2 = self._make_requirement_with_points(requirement)
        pipeline = FakeTwoStagePipeline(FakeCaseGenerator(_cases()), FakeReviewer())
        service = GenerationService(pipeline=pipeline)

        record = service.generate_from_test_points(requirement, [tp1.id, tp2.id])

        assert record.status == "success"
        assert record.review_result is not None
        assert TestCase.objects.filter(requirement=requirement).count() == 2
        assert TestCase.objects.get(case_id="TC_001").test_point == tp1
        assert TestCase.objects.get(case_id="TC_002").test_point == tp2
        # 测试点本身不被删除或改动
        assert TestPoint.objects.filter(requirement=requirement).count() == 2

    def test_generate_without_selection_raises(self, requirement):
        pipeline = FakeTwoStagePipeline(FakeCaseGenerator(_cases()), FakeReviewer())
        service = GenerationService(pipeline=pipeline)
        with pytest.raises(BadRequestError):
            service.generate_from_test_points(requirement, [])

    def test_generate_failure_records_error(self, requirement):
        tp1, _ = self._make_requirement_with_points(requirement)

        class RaisingGenerator:
            def generate(self, *args, **kwargs):
                raise RuntimeError("mock LLM 故障")

        pipeline = FakeTwoStagePipeline(RaisingGenerator(), FakeReviewer())
        service = GenerationService(pipeline=pipeline)
        with pytest.raises(RuntimeError):
            service.generate_from_test_points(requirement, [tp1.id])

        record = GenerationRecord.objects.filter(requirement=requirement).first()
        assert record.status == "failed"
        assert "LLM 故障" in record.error_message


@pytest.mark.django_db
class TestTestPointAPI:
    def test_generate_testpoints(self, api_client, requirement):
        with patch("testcases.views_api.GenerationService") as mock_svc:
            mock_svc.return_value.generate_test_points.return_value = []
            resp = api_client.post(f"/api/requirements/{requirement.id}/testpoints/generate/")
            assert resp.status_code == 200
            assert resp.json()["code"] == 0
            mock_svc.return_value.generate_test_points.assert_called_once()

    def test_create_testpoint(self, api_client, requirement):
        resp = api_client.post(
            f"/api/requirements/{requirement.id}/testpoints/",
            {"title": "点", "category": "normal", "priority": "P0"},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["title"] == "点"
        assert resp.json()["data"]["selected"] is True

    def test_patch_toggle_selected(self, api_client, requirement):
        tp = TestPoint.objects.create(requirement=requirement, title="点", category="normal", priority="P0")
        resp = api_client.patch(
            f"/api/requirements/{requirement.id}/testpoints/{tp.id}/",
            {"selected": False},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["selected"] is False
        tp.refresh_from_db()
        assert tp.selected is False

    def test_delete_testpoint(self, api_client, requirement):
        tp = TestPoint.objects.create(requirement=requirement, title="点", category="normal", priority="P0")
        resp = api_client.delete(f"/api/requirements/{requirement.id}/testpoints/{tp.id}/")
        assert resp.status_code == 200
        assert TestPoint.objects.filter(id=tp.id).count() == 0

    def test_batch_select(self, api_client, requirement):
        TestPoint.objects.create(requirement=requirement, title="a", category="normal", priority="P0")
        TestPoint.objects.create(requirement=requirement, title="b", category="normal", priority="P0")
        resp = api_client.post(
            f"/api/requirements/{requirement.id}/testpoints/select/",
            {"selected": False},
            format="json",
        )
        assert resp.status_code == 200
        assert TestPoint.objects.filter(requirement=requirement, selected=False).count() == 2

    def test_generate_cases_from_points(self, api_client, requirement):
        with patch("testcases.views_api.GenerationService") as mock_svc:
            record = GenerationRecord.objects.create(
                requirement=requirement, status="success", model="deepseek-chat"
            )
            mock_svc.return_value.generate_from_test_points.return_value = record
            resp = api_client.post(
                f"/api/requirements/{requirement.id}/testcases/generate/",
                {"test_point_ids": [1, 2]},
                format="json",
            )
            assert resp.status_code == 200
            assert resp.json()["code"] == 0
            mock_svc.return_value.generate_from_test_points.assert_called_once()
