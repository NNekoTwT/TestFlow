"""需求解析阶段的结构化输出 Schema。"""
from pydantic import BaseModel, Field


class InputField(BaseModel):
    """输入字段及其约束。"""

    name: str = Field(default="", description="字段名")
    description: str = Field(default="", description="字段说明")
    constraints: list[str] = Field(default_factory=list, description="字段约束")


class RequirementAnalysis(BaseModel):
    """需求解析结果。"""

    feature_points: list[str] = Field(default_factory=list, description="功能点")
    input_fields: list[InputField] = Field(default_factory=list, description="输入字段")
    input_constraints: list[str] = Field(default_factory=list, description="输入约束")
    business_rules: list[str] = Field(default_factory=list, description="业务规则")
    state_changes: list[str] = Field(default_factory=list, description="状态变化")
    exception_conditions: list[str] = Field(default_factory=list, description="异常条件")
    boundary_conditions: list[str] = Field(default_factory=list, description="边界条件")
    preconditions: list[str] = Field(default_factory=list, description="前置条件")
    uncertain_points: list[str] = Field(default_factory=list, description="无法确定的信息")
