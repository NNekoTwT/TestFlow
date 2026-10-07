"""第二阶段：测试点生成（Test Point Generator）。"""
import logging

from ai.prompts import testpoint_generator as prompt
from ai.schemas.analysis import RequirementAnalysis
from ai.schemas.testpoint import TestPointList
from core.llm import build_llm

from .base import call_with_schema, schema_json

logger = logging.getLogger("testflow.ai")


class TestPointGenerator:
    """根据解析结果设计测试点，并标注分类与测试设计方法。"""

    __test__ = False  # 避免 pytest 误收集

    def __init__(self, llm=None):
        self.llm = llm

    def generate(self, description, analysis: RequirementAnalysis) -> list:
        llm = self.llm or build_llm(temperature=0.1)
        user_prompt = prompt.USER_TEMPLATE.format(
            description=description,
            analysis_json=analysis.model_dump_json(indent=2),
            json_schema=schema_json(TestPointList),
        )
        data = call_with_schema(llm, prompt.SYSTEM_PROMPT, user_prompt)
        result = TestPointList.model_validate(data)
        logger.info("测试点生成完成：%d 个", len(result.test_points))
        return result.test_points
