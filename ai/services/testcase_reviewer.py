"""第四阶段：测试用例质量检查（Test Case Reviewer）。"""
import logging

from ai.prompts import testcase_reviewer as prompt
from ai.schemas.review import ReviewResult
from core.llm import build_llm

from .base import call_with_schema, schema_json

logger = logging.getLogger("testflow.ai")


class TestCaseReviewer:
    """对生成的测试用例进行辅助性质量检查（不声称覆盖完整）。"""

    __test__ = False  # 避免 pytest 误收集

    def __init__(self, llm=None):
        self.llm = llm

    def review(self, description, test_cases) -> ReviewResult:
        llm = self.llm or build_llm(temperature=0.1)
        user_prompt = prompt.USER_TEMPLATE.format(
            description=description,
            test_cases_text=self._format_cases(test_cases),
            json_schema=schema_json(ReviewResult),
        )
        data = call_with_schema(llm, prompt.SYSTEM_PROMPT, user_prompt)
        result = ReviewResult.model_validate(data)
        logger.info("用例评审完成：问题 %d 条", len(result.coverage_issues))
        return result

    @staticmethod
    def _format_cases(test_cases):
        lines = []
        for tc in test_cases:
            steps = tc.steps if isinstance(tc.steps, list) else [tc.steps]
            lines.append(
                f"[{tc.case_id}] ({tc.priority}/{tc.test_type}) {tc.title}\n"
                f"  步骤：{'；'.join(steps)}\n"
                f"  预期：{tc.expected_result}"
            )
        return "\n".join(lines)
