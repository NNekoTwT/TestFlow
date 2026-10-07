"""生成编排服务测试：测试用例保存 / 评审结果解析 / 向量索引 / 失败记录。"""
import pytest
from django.conf import settings

from testcases.models import GenerationRecord, TestCase, TestPoint
from testcases.services import GenerationService


@pytest.mark.django_db
class TestGenerationService:
    def test_generate_persists_data(self, requirement, fake_pipeline):
        service = GenerationService(pipeline=fake_pipeline)
        record = service.generate(requirement)

        assert record.status == "success"
        assert record.review_result is not None
        assert record.duration_ms >= 0

        assert TestPoint.objects.filter(requirement=requirement).count() == 3
        assert TestCase.objects.filter(requirement=requirement).count() == 3

        tc = TestCase.objects.get(case_id="TC_001")
        assert tc.test_type == "normal"
        assert tc.priority == "P0"
        # 步骤与前置条件应以 JSON 数组保存
        assert isinstance(tc.steps, list)
        assert len(tc.steps) == 3

    def test_generate_links_test_point(self, requirement, fake_pipeline):
        service = GenerationService(pipeline=fake_pipeline)
        service.generate(requirement)

        tc = TestCase.objects.get(case_id="TC_001")
        assert tc.test_point is not None
        assert "正确手机号" in tc.test_point.title

    def test_regenerate_replaces_old_data(self, requirement, fake_pipeline):
        service = GenerationService(pipeline=fake_pipeline)
        service.generate(requirement)
        service.generate(requirement)

        # 第二次生成应替换而非累加
        assert TestCase.objects.filter(requirement=requirement).count() == 3
        assert GenerationRecord.objects.filter(requirement=requirement).count() == 2

    def test_failure_records_error(self, requirement):
        class RaisingPipeline:
            def run(self, *args, **kwargs):
                raise RuntimeError("mock 的 LLM 故障")

        service = GenerationService(pipeline=RaisingPipeline())
        with pytest.raises(RuntimeError):
            service.generate(requirement)

        record = GenerationRecord.objects.get(requirement=requirement)
        assert record.status == "failed"
        assert "LLM 故障" in record.error_message

    def test_find_similar_empty_when_no_index(self, requirement):
        service = GenerationService()
        assert service.find_similar_cases(requirement) == []
