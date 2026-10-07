"""测试用例生成阶段的结构化输出 Schema。"""
from typing import Literal

from pydantic import BaseModel, Field


class TestCase(BaseModel):
    """单条测试用例。"""

    __test__ = False  # 避免 pytest 将数据类误收集为测试类

    case_id: str = Field(description="用例编号")
    module: str = Field(default="", description="所属模块")
    title: str = Field(description="用例标题")
    preconditions: list[str] = Field(default_factory=list, description="前置条件")
    steps: list[str] = Field(default_factory=list, description="测试步骤")
    test_data: str = Field(default="", description="测试数据")
    expected_result: str = Field(description="预期结果")
    test_type: Literal["normal", "exception", "boundary"] = Field(description="用例类型")
    priority: Literal["P0", "P1", "P2", "P3"] = Field(description="优先级")
    design_method: Literal[
        "equivalence_partitioning", "boundary_value", "scenario", "state_transition", "other"
    ] = Field(description="测试设计方法")
    test_point_index: int | None = Field(
        default=None, description="来源测试点在输入列表中的下标（从 0 开始，可为 null）"
    )


class TestCaseList(BaseModel):
    test_cases: list[TestCase] = Field(default_factory=list)
