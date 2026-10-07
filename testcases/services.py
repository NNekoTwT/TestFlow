"""测试用例生成业务编排层。

职责：
1. 检索相似历史用例（向量检索 + MySQL 取完整数据）
2. 调用 AI 流水线（解析 -> 测试点 -> 用例 -> 评审）
3. 持久化测试点 / 测试用例 / 生成记录
4. 将测试用例向量化并写入向量库
"""
import logging
import time

from django.conf import settings
from django.db import transaction

from ai.schemas.testpoint import TestPoint as TestPointSchema
from ai.services.orchestrator import AIPipeline
from core.embeddings import get_embedding_client
from core.exceptions import BadRequestError
from vectorstore import get_vector_store

from .models import GenerationRecord, TestCase, TestPoint

logger = logging.getLogger("testflow")


class GenerationService:
    """AI 测试用例生成的编排与持久化。"""

    def __init__(self, pipeline=None):
        # 可注入自定义 pipeline，便于测试
        self.pipeline = pipeline or AIPipeline()

    # ------------------------------------------------------------------
    # 主流程
    # ------------------------------------------------------------------
    def generate(self, requirement, generation_record=None):
        """执行完整生成流程，返回 GenerationRecord。

        失败时抛出异常（由上层统一处理），但会先落一条 failed 记录。
        """
        start = time.monotonic()
        record = generation_record or GenerationRecord.objects.create(
            requirement=requirement,
            status="running",
            model=settings.DEEPSEEK_MODEL,
        )

        try:
            similar_cases = self._similar_to_dicts(self.find_similar_cases(requirement))
            result = self.pipeline.run(
                requirement.title,
                requirement.module,
                requirement.description,
                similar_cases=similar_cases,
            )
            self._replace(requirement, result)
            record.status = "success"
            record.review_result = result.review.model_dump()
        except Exception as exc:
            record.status = "failed"
            record.error_message = str(exc)
            logger.exception("测试用例生成失败（requirement_id=%s）：%s", requirement.id, exc)
            raise
        finally:
            record.duration_ms = int((time.monotonic() - start) * 1000)
            record.save(
                update_fields=["status", "error_message", "duration_ms", "review_result"]
            )
        return record

    # ------------------------------------------------------------------
    # 分阶段流程：只生成测试点 / 按已选测试点生成用例
    # ------------------------------------------------------------------
    def generate_test_points(self, requirement):
        """只执行「需求解析 -> 测试点生成」，替换该需求已有测试点。

        不生成测试用例，也不跑评审。返回保存后的 TestPoint 实例列表。
        """
        points = self.pipeline.generate_test_points(
            requirement.title, requirement.module, requirement.description
        )
        with transaction.atomic():
            requirement.test_points.all().delete()
            saved = self._save_test_points(requirement, points)
        logger.info("测试点生成完成（requirement_id=%s）：%d 个", requirement.id, len(saved))
        return saved

    def generate_from_test_points(self, requirement, test_point_ids):
        """根据用户选择的测试点生成测试用例，并关联回对应测试点。

        只跑「测试用例生成 -> 评审」两阶段，测试点不再重新生成。
        失败时抛出异常，但会落一条 failed 记录。
        """
        test_points = list(
            TestPoint.objects.filter(id__in=test_point_ids, requirement=requirement)
        )
        if not test_points:
            raise BadRequestError("请先选择至少一个测试点")

        schema_points = [
            TestPointSchema(
                title=tp.title,
                description=tp.description,
                category=tp.category,
                priority=tp.priority,
                design_method=tp.design_method,
            )
            for tp in test_points
        ]
        similar_cases = self._similar_to_dicts(self.find_similar_cases(requirement))

        record = GenerationRecord.objects.create(
            requirement=requirement,
            status="running",
            model=settings.DEEPSEEK_MODEL,
        )
        start = time.monotonic()
        try:
            test_cases = self.pipeline.testcase_generator.generate(
                requirement.module, requirement.description, schema_points, similar_cases
            )
            review = self.pipeline.reviewer.review(requirement.description, test_cases)
            with transaction.atomic():
                requirement.test_cases.all().delete()
                saved = self._save_test_cases(requirement, test_points, test_cases)
            self._reindex(requirement, saved)
            record.status = "success"
            record.review_result = review.model_dump()
        except Exception as exc:
            record.status = "failed"
            record.error_message = str(exc)
            logger.exception("按测试点生成用例失败（requirement_id=%s）：%s", requirement.id, exc)
            raise
        finally:
            record.duration_ms = int((time.monotonic() - start) * 1000)
            record.save(
                update_fields=["status", "error_message", "duration_ms", "review_result"]
            )
        return record

    # ------------------------------------------------------------------
    # 相似用例检索
    # ------------------------------------------------------------------
    def find_similar_cases(self, requirement, top_k=None):
        """向量检索相似历史用例，返回 TestCase 实例列表（按相似度排序）。

        任何向量库异常都降级为空列表，不影响核心生成流程。
        """
        top_k = top_k or settings.SIMILAR_TOP_K
        store = get_vector_store()
        try:
            embedding = get_embedding_client()
            vector = embedding.embed_one(self._requirement_text(requirement))
            hits = store.search(vector, top_k=top_k)
        except Exception as exc:
            logger.warning("相似用例检索失败（降级为空）：%s", exc)
            return []

        # 排除本需求自身的用例，避免自引用
        ids = [
            h["id"]
            for h in hits
            if h.get("id")
            and str(h.get("payload", {}).get("requirement_id")) != str(requirement.id)
        ]
        if not ids:
            return []

        cases = TestCase.objects.filter(pk__in=ids)
        by_id = {str(c.pk): c for c in cases}
        return [by_id[i] for i in ids if i in by_id]

    # ------------------------------------------------------------------
    # 持久化
    # ------------------------------------------------------------------
    def _replace(self, requirement, result):
        """替换旧数据：删除旧的测试点 / 用例，写入新结果。"""
        with transaction.atomic():
            requirement.test_points.all().delete()
            requirement.test_cases.all().delete()
            test_points = self._save_test_points(requirement, result.test_points)
            test_cases = self._save_test_cases(requirement, test_points, result.test_cases)

        self._reindex(requirement, test_cases)

    def _save_test_points(self, requirement, test_points):
        saved = []
        for tp in test_points:
            saved.append(
                TestPoint.objects.create(
                    requirement=requirement,
                    title=tp.title,
                    description=getattr(tp, "description", "") or "",
                    category=tp.category,
                    priority=getattr(tp, "priority", "P1") or "P1",
                    design_method=getattr(tp, "design_method", "other") or "other",
                )
            )
        return saved

    def _save_test_cases(self, requirement, test_points, test_cases):
        saved = []
        for tc in test_cases:
            test_point = None
            if tc.test_point_index is not None and 0 <= tc.test_point_index < len(test_points):
                test_point = test_points[tc.test_point_index]
            saved.append(
                TestCase.objects.create(
                    requirement=requirement,
                    test_point=test_point,
                    case_id=tc.case_id,
                    module=tc.module or requirement.module,
                    title=tc.title,
                    preconditions=tc.preconditions,
                    steps=tc.steps,
                    test_data=tc.test_data,
                    expected_result=tc.expected_result,
                    test_type=tc.test_type,
                    priority=tc.priority,
                    design_method=tc.design_method,
                )
            )
        return saved

    # ------------------------------------------------------------------
    # 向量索引
    # ------------------------------------------------------------------
    def _reindex(self, requirement, test_cases):
        """清理旧向量后，将新用例向量化并写入向量库。"""
        store = get_vector_store()
        try:
            store.delete_by_requirement(requirement.id)
        except Exception as exc:
            logger.warning("清理旧向量失败（不影响主流程）：%s", exc)

        if not test_cases:
            return

        embedding = get_embedding_client()
        texts = [self._testcase_text(tc) for tc in test_cases]
        vectors = embedding.embed(texts)

        items = [
            {
                "id": str(tc.pk),
                "vector": vector,
                "payload": {
                    "testcase_id": tc.case_id,
                    "requirement_id": requirement.id,
                },
            }
            for tc, vector in zip(test_cases, vectors)
        ]
        try:
            store.insert(items)
            logger.info("已写入 %d 条用例向量", len(items))
        except Exception as exc:
            # 向量库写入失败不应影响核心流程（数据已落 MySQL）
            logger.warning("向量写入失败（不影响主流程）：%s", exc)

    # ------------------------------------------------------------------
    # 工具方法
    # ------------------------------------------------------------------
    @staticmethod
    def _requirement_text(requirement):
        return f"{requirement.title} {requirement.module} {requirement.description}"

    @staticmethod
    def _testcase_text(testcase):
        steps = testcase.steps if isinstance(testcase.steps, list) else []
        return " ".join([testcase.title, " ".join(steps), testcase.expected_result or ""])

    @staticmethod
    def _similar_to_dicts(cases):
        return [
            {
                "case_id": c.case_id,
                "title": c.title,
                "steps": c.steps,
                "expected_result": c.expected_result,
            }
            for c in cases
        ]
