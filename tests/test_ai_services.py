"""AI Service 单元测试：结构化 LLM 输出解析（Mock 掉真实 API）。"""
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from ai.schemas.analysis import RequirementAnalysis
from ai.schemas.review import ReviewResult
from ai.schemas.testcase import TestCase
from ai.schemas.testpoint import TestPoint
from ai.services.requirement_analyzer import RequirementAnalyzer
from ai.services.testcase_generator import TestCaseGenerator
from ai.services.testcase_reviewer import TestCaseReviewer
from ai.services.testpoint_generator import TestPointGenerator


def _analyzer_payload():
    return {
        "feature_points": ["用户登录"],
        "input_fields": [{"name": "手机号", "description": "", "constraints": ["11 位数字"]}],
        "input_constraints": ["密码长度 8~20 位"],
        "business_rules": ["连续错误 5 次锁定 30 分钟"],
        "state_changes": ["未登录 -> 已登录"],
        "exception_conditions": ["锁定期间登录"],
        "boundary_conditions": ["密码长度 8/20"],
        "preconditions": ["账号已注册"],
        "uncertain_points": [],
    }


class TestRequirementAnalyzer:
    def test_parse_valid_json(self):
        analyzer = RequirementAnalyzer(llm=MagicMock())
        with patch("ai.services.base.invoke_json", return_value=_analyzer_payload()):
            result = analyzer.analyze("用户登录", "登录模块", "手机号登录")
        assert isinstance(result, RequirementAnalysis)
        assert result.feature_points == ["用户登录"]
        assert result.input_fields[0].name == "手机号"
        assert len(result.business_rules) == 1

    def test_parse_invalid_type_raises(self):
        analyzer = RequirementAnalyzer(llm=MagicMock())
        bad = _analyzer_payload()
        bad["feature_points"] = "not-a-list"
        with patch("ai.services.base.invoke_json", return_value=bad):
            with pytest.raises(ValidationError):
                analyzer.analyze("用户登录", "登录模块", "手机号登录")


class TestTestPointGenerator:
    def test_parse_valid_json(self):
        gen = TestPointGenerator(llm=MagicMock())
        analysis = RequirementAnalysis.model_validate(_analyzer_payload())
        payload = {
            "test_points": [
                {"title": "正常登录", "category": "normal", "priority": "P0", "design_method": "scenario"},
                {"title": "密码边界", "category": "boundary", "priority": "P1", "design_method": "boundary_value"},
            ]
        }
        with patch("ai.services.base.invoke_json", return_value=payload):
            points = gen.generate("手机号登录", analysis)
        assert len(points) == 2
        assert points[0].category == "normal"
        assert points[0].priority == "P0"
        assert points[1].design_method == "boundary_value"


class TestTestCaseGenerator:
    def test_parse_valid_json(self):
        gen = TestCaseGenerator(llm=MagicMock())
        payload = {
            "test_cases": [
                {
                    "case_id": "TC_001",
                    "module": "登录模块",
                    "title": "登录成功",
                    "preconditions": [],
                    "steps": ["输入手机号", "点击登录"],
                    "test_data": "",
                    "expected_result": "跳转首页",
                    "test_type": "normal",
                    "priority": "P0",
                    "design_method": "scenario",
                    "test_point_index": 0,
                }
            ]
        }
        points = [TestPoint(title="正常登录", category="normal", priority="P0", design_method="scenario")]
        with patch("ai.services.base.invoke_json", return_value=payload):
            cases = gen.generate("登录模块", "手机号登录", points, similar_cases=None)
        assert len(cases) == 1
        assert isinstance(cases[0], TestCase)
        assert cases[0].priority == "P0"

    def test_empty_similar_cases_text(self):
        gen = TestCaseGenerator(llm=MagicMock())
        assert "无相似" in gen._format_similar(None)
        assert "无相似" in gen._format_similar([])


class TestTestCaseReviewer:
    def test_parse_valid_json(self):
        reviewer = TestCaseReviewer(llm=MagicMock())
        payload = {
            "coverage_issues": ["遗漏异常场景"],
            "missing_scenarios": ["锁定期间登录"],
            "duplicate_candidates": [],
            "ambiguous_cases": [],
            "suggestions": ["补充边界值用例"],
        }
        cases = [
            TestCase(
                case_id="TC_001",
                module="登录模块",
                title="登录成功",
                preconditions=[],
                steps=["输入手机号"],
                test_data="",
                expected_result="跳转首页",
                test_type="normal",
                priority="P0",
                design_method="scenario",
            )
        ]
        with patch("ai.services.base.invoke_json", return_value=payload):
            result = reviewer.review("手机号登录", cases)
        assert isinstance(result, ReviewResult)
        assert result.missing_scenarios == ["锁定期间登录"]
