"""测试点生成阶段的结构化输出 Schema。"""
from typing import Literal

from pydantic import BaseModel, Field

# 测试维度（与 testcases.models.TEST_POINT_CATEGORY_CHOICES 保持一致）
CATEGORY_LITERAL = Literal[
    "normal",
    "exception",
    "boundary",
    "input_validation",
    "state_transition",
    "permission",
    "data_consistency",
    "security",
    "performance",
    "compatibility",
    "usability",
    "other",
]

DESIGN_METHOD_LITERAL = Literal[
    "equivalence_partitioning", "boundary_value", "scenario", "state_transition", "other"
]


class TestPoint(BaseModel):
    """单个测试点（描述「应该测哪些场景」，而非详细步骤）。"""

    __test__ = False  # 避免 pytest 将数据类误收集为测试类

    title: str = Field(description="测试点标题（简短）")
    description: str = Field(default="", description="测试点描述（说明要验证什么）")
    category: CATEGORY_LITERAL = Field(description="测试维度分类")
    priority: Literal["P0", "P1", "P2"] = Field(description="优先级：P0 核心流程/严重风险，P1 重要异常/边界，P2 普通低风险")
    design_method: DESIGN_METHOD_LITERAL = Field(default="other", description="测试设计方法")


class TestPointList(BaseModel):
    test_points: list[TestPoint] = Field(default_factory=list)
