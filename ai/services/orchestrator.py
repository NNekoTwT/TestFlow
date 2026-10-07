"""AI 生成流水线编排。

流程（对应 README 中的 Mermaid 图）：
    Requirement Analysis -> Test Point Generation
        -> (相似检索在业务层完成) -> Test Case Generation -> Quality Review

这里只做纯 AI 调用编排，不直接操作数据库；
数据库落库与向量检索由业务层（testcases.services）负责，
这样 AI 层可独立单元测试。
"""
from dataclasses import dataclass

from ai.schemas.analysis import RequirementAnalysis
from ai.schemas.review import ReviewResult
from ai.schemas.testcase import TestCase
from ai.schemas.testpoint import TestPoint
from ai.services.requirement_analyzer import RequirementAnalyzer
from ai.services.testcase_generator import TestCaseGenerator
from ai.services.testcase_reviewer import TestCaseReviewer
from ai.services.testpoint_generator import TestPointGenerator


@dataclass
class PipelineResult:
    analysis: RequirementAnalysis
    test_points: list[TestPoint]
    test_cases: list[TestCase]
    review: ReviewResult


class AIPipeline:
    """串联四个 AI 阶段。各阶段可注入以方便测试与替换。"""

    def __init__(
        self,
        analyzer=None,
        testpoint_generator=None,
        testcase_generator=None,
        reviewer=None,
    ):
        self.analyzer = analyzer or RequirementAnalyzer()
        self.testpoint_generator = testpoint_generator or TestPointGenerator()
        self.testcase_generator = testcase_generator or TestCaseGenerator()
        self.reviewer = reviewer or TestCaseReviewer()

    def run(self, title, module, description, similar_cases=None) -> PipelineResult:
        analysis = self.analyzer.analyze(title, module, description)
        test_points = self.testpoint_generator.generate(description, analysis)
        test_cases = self.testcase_generator.generate(
            module, description, test_points, similar_cases
        )
        review = self.reviewer.review(description, test_cases)
        return PipelineResult(
            analysis=analysis,
            test_points=test_points,
            test_cases=test_cases,
            review=review,
        )

    def generate_test_points(self, title, module, description) -> list[TestPoint]:
        """只执行「需求解析 -> 测试点生成」两阶段，供独立的测试点生成入口使用。"""
        analysis = self.analyzer.analyze(title, module, description)
        return self.testpoint_generator.generate(description, analysis)
