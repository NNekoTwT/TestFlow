"""测试用例质量检查（Reviewer）阶段的结构化输出 Schema。"""
from pydantic import BaseModel, Field


class ReviewResult(BaseModel):
    """AI Reviewer 输出。仅作辅助检查，不声称可证明覆盖完整。"""

    coverage_issues: list[str] = Field(default_factory=list, description="覆盖性 / 完整性问题")
    missing_scenarios: list[str] = Field(default_factory=list, description="遗漏的场景")
    duplicate_candidates: list[str] = Field(default_factory=list, description="疑似重复的用例")
    ambiguous_cases: list[str] = Field(default_factory=list, description="模糊、不可执行的用例")
    suggestions: list[str] = Field(default_factory=list, description="改进建议")
