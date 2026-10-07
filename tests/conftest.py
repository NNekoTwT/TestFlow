"""pytest 全局 fixtures。"""
import pytest

from ai.schemas.analysis import RequirementAnalysis
from ai.schemas.review import ReviewResult
from ai.schemas.testcase import TestCase
from ai.schemas.testpoint import TestPoint
from ai.services.orchestrator import PipelineResult
from vectorstore import reset_vector_store


@pytest.fixture(autouse=True)
def _reset_vector_store():
    """每个用例前后重置向量库单例，避免状态串扰。"""
    reset_vector_store()
    yield
    reset_vector_store()


@pytest.fixture
def requirement(db):
    from requirements.models import Requirement

    return Requirement.objects.create(
        title="用户登录",
        module="登录模块",
        description=(
            "用户使用手机号和密码登录。手机号必须为 11 位数字。"
            "密码长度为 8~20 位。连续输入错误密码 5 次后，账号锁定 30 分钟。"
            "账号锁定期间禁止登录。登录成功后跳转首页。"
        ),
    )


def make_pipeline_result():
    """构造一个固定的 PipelineResult，供生成流程测试使用。"""
    analysis = RequirementAnalysis(
        feature_points=["用户登录"],
        input_fields=[],
        input_constraints=["手机号必须为 11 位数字", "密码长度 8~20 位"],
        business_rules=["连续输入错误密码 5 次后锁定 30 分钟"],
        state_changes=["未登录 -> 已登录", "正常 -> 锁定"],
        exception_conditions=["账号锁定期间登录"],
        boundary_conditions=["密码长度 8 / 20", "错误次数 5"],
        preconditions=["账号已注册"],
        uncertain_points=[],
    )
    test_points = [
        TestPoint(title="正确手机号和密码登录成功", description="", category="normal", priority="P0", design_method="scenario"),
        TestPoint(title="密码长度边界值", description="验证 8/20 位边界", category="boundary", priority="P1", design_method="boundary_value"),
        TestPoint(title="连续错误 5 次锁定", description="", category="exception", priority="P0", design_method="state_transition"),
    ]
    test_cases = [
        TestCase(
            case_id="TC_001",
            module="登录模块",
            title="正确手机号密码登录成功",
            preconditions=["账号已注册且未锁定"],
            steps=["输入正确手机号", "输入正确密码", "点击登录"],
            test_data="手机号=13800138000，密码=12345678",
            expected_result="登录成功并跳转首页",
            test_type="normal",
            priority="P0",
            design_method="scenario",
            test_point_index=0,
        ),
        TestCase(
            case_id="TC_002",
            module="登录模块",
            title="密码长度为 7 位时登录失败",
            preconditions=[],
            steps=["输入 7 位密码", "点击登录"],
            test_data="密码=1234567",
            expected_result="提示密码长度需为 8~20 位，登录失败",
            test_type="boundary",
            priority="P1",
            design_method="boundary_value",
            test_point_index=1,
        ),
        TestCase(
            case_id="TC_003",
            module="登录模块",
            title="连续错误 5 次后账号锁定 30 分钟",
            preconditions=["账号未锁定"],
            steps=["连续输入 5 次错误密码"],
            test_data="错误密码重复 5 次",
            expected_result="第 5 次后账号锁定 30 分钟，期间禁止登录",
            test_type="exception",
            priority="P0",
            design_method="state_transition",
            test_point_index=2,
        ),
    ]
    review = ReviewResult(
        coverage_issues=["未覆盖手机号非 11 位的异常场景"],
        missing_scenarios=["手机号长度不等于 11 位"],
        duplicate_candidates=[],
        ambiguous_cases=[],
        suggestions=["补充手机号非法输入的用例"],
    )
    return PipelineResult(
        analysis=analysis,
        test_points=test_points,
        test_cases=test_cases,
        review=review,
    )


class FakePipeline:
    """记录调用并返回固定结果的假流水线。"""

    def __init__(self, result):
        self.result = result
        self.calls = []

    def run(self, title, module, description, similar_cases=None):
        self.calls.append(
            {
                "title": title,
                "module": module,
                "description": description,
                "similar_cases": similar_cases,
            }
        )
        return self.result


@pytest.fixture
def pipeline_result():
    return make_pipeline_result()


@pytest.fixture
def fake_pipeline(pipeline_result):
    return FakePipeline(pipeline_result)
