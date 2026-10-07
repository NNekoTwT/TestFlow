"""API 测试：需求 CRUD、生成接口、参数校验、异常请求。"""
from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from testcases.models import GenerationRecord


@pytest.fixture
def api_client():
    return APIClient()


VALID_REQUIREMENT = {
    "title": "用户登录",
    "module": "登录模块",
    "description": "用户使用手机号和密码登录。密码长度 8~20 位。",
}


@pytest.mark.django_db
class TestRequirementCRUD:
    def test_create_requirement(self, api_client):
        resp = api_client.post("/api/requirements/", VALID_REQUIREMENT, format="json")
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        assert body["data"]["title"] == "用户登录"
        assert body["data"]["id"] is not None

    def test_list_requirements(self, api_client, requirement):
        resp = api_client.get("/api/requirements/")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) >= 1

    def test_get_requirement_detail(self, api_client, requirement):
        resp = api_client.get(f"/api/requirements/{requirement.id}/")
        assert resp.status_code == 200
        assert resp.json()["data"]["title"] == "用户登录"

    def test_get_not_found(self, api_client):
        resp = api_client.get("/api/requirements/999999/")
        assert resp.status_code == 404
        assert resp.json()["code"] == 404

    def test_create_missing_title(self, api_client):
        data = {"module": "登录模块", "description": "无标题"}
        resp = api_client.post("/api/requirements/", data, format="json")
        assert resp.status_code == 400
        assert resp.json()["code"] == 400

    def test_create_invalid_json(self, api_client):
        resp = api_client.post(
            "/api/requirements/", "这不是JSON", content_type="application/json"
        )
        assert resp.status_code == 400


@pytest.mark.django_db
class TestGenerateAPI:
    def test_generate_basic_flow(self, api_client, requirement):
        from testcases.models import GenerationRecord

        with patch("testcases.views_api.GenerationService") as mock_svc:
            record = GenerationRecord.objects.create(
                requirement=requirement, status="success", model="deepseek-chat"
            )
            mock_svc.return_value.generate.return_value = record

            resp = api_client.post(f"/api/requirements/{requirement.id}/generate/")
            assert resp.status_code == 200
            body = resp.json()
            assert body["code"] == 0
            assert body["data"]["generation"]["status"] == "success"
            mock_svc.return_value.generate.assert_called_once()

    def test_generate_without_api_key_returns_error(self, api_client, requirement, settings):
        settings.DEEPSEEK_API_KEY = ""
        resp = api_client.post(f"/api/requirements/{requirement.id}/generate/")
        assert resp.status_code == 503
        assert resp.json()["code"] == 503
        # 应落一条 failed 记录
        record = GenerationRecord.objects.filter(requirement=requirement).first()
        assert record is not None
        assert record.status == "failed"

    def test_generate_not_found(self, api_client):
        resp = api_client.post("/api/requirements/999999/generate/")
        assert resp.status_code == 404


@pytest.mark.django_db
class TestQueryAPIs:
    def test_testcases_empty(self, api_client, requirement):
        resp = api_client.get(f"/api/requirements/{requirement.id}/testcases/")
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    def test_review_not_generated(self, api_client, requirement):
        resp = api_client.get(f"/api/requirements/{requirement.id}/review/")
        assert resp.status_code == 404

    def test_similar_empty(self, api_client, requirement):
        resp = api_client.get(f"/api/requirements/{requirement.id}/similar/")
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    def test_export_empty_returns_404(self, api_client, requirement):
        resp = api_client.get(f"/api/requirements/{requirement.id}/export/excel/")
        assert resp.status_code == 404
