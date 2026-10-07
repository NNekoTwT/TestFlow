"""第三阶段：测试用例生成（Test Case Generator）。"""
import json
import logging

from ai.prompts import testcase_generator as prompt
from ai.schemas.testcase import TestCaseList
from core.llm import build_llm

from .base import call_with_schema, schema_json

logger = logging.getLogger("testflow.ai")


class TestCaseGenerator:
    """根据测试点 + 相似历史用例生成结构化测试用例。"""

    __test__ = False  # 避免 pytest 误收集

    def __init__(self, llm=None):
        self.llm = llm

    def generate(self, module, description, test_points, similar_cases=None) -> list:
        llm = self.llm or build_llm(temperature=0.1)
        test_points_json = json.dumps(
            [tp.model_dump() for tp in test_points], ensure_ascii=False, indent=2
        )
        user_prompt = prompt.USER_TEMPLATE.format(
            module=module,
            description=description,
            test_points_json=test_points_json,
            similar_cases_text=self._format_similar(similar_cases),
            json_schema=schema_json(TestCaseList),
        )
        data = call_with_schema(llm, prompt.SYSTEM_PROMPT, user_prompt)
        result = TestCaseList.model_validate(data)
        logger.info("测试用例生成完成：%d 条", len(result.test_cases))
        return result.test_cases

    @staticmethod
    def _format_similar(similar_cases):
        """将相似历史用例（dict 列表）格式化为纯文本上下文。"""
        if not similar_cases:
            return "（无相似历史用例）"

        lines = []
        for i, item in enumerate(similar_cases, 1):
            case_id = item.get("case_id", "-")
            title = item.get("title", "")
            steps = item.get("steps") or []
            if isinstance(steps, str):
                steps = [steps]
            expected = item.get("expected_result", "")
            lines.append(
                f"{i}. [{case_id}] {title}\n"
                f"   步骤：{'；'.join(steps)}\n"
                f"   预期：{expected}"
            )
        return "\n".join(lines)
