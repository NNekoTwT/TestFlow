"""第一阶段：需求解析（Requirement Analyzer）。"""
import logging

from ai.prompts import requirement_analyzer as prompt
from ai.schemas.analysis import RequirementAnalysis
from core.llm import build_llm

from .base import call_with_schema, schema_json

logger = logging.getLogger("testflow.ai")


class RequirementAnalyzer:
    """从需求中提取功能点、输入字段、业务规则等结构化信息。"""

    def __init__(self, llm=None):
        self.llm = llm

    def analyze(self, title, module, description) -> RequirementAnalysis:
        llm = self.llm or build_llm(temperature=0.1)
        user_prompt = prompt.USER_TEMPLATE.format(
            title=title,
            module=module,
            description=description,
            json_schema=schema_json(RequirementAnalysis),
        )
        data = call_with_schema(llm, prompt.SYSTEM_PROMPT, user_prompt)
        result = RequirementAnalysis.model_validate(data)
        logger.info("需求解析完成：功能点 %d 个", len(result.feature_points))
        return result
