from django.db import models


CATEGORY_CHOICES = [
    ("normal", "正常"),
    ("exception", "异常"),
    ("boundary", "边界"),
]

# 测试点分类（维度）与测试用例类型（test_type）语义不同，拆开定义。
# 测试点关注「应该测哪些维度」，因此分类更丰富。
TEST_POINT_CATEGORY_CHOICES = [
    ("normal", "功能测试"),
    ("exception", "异常测试"),
    ("boundary", "边界测试"),
    ("input_validation", "输入校验"),
    ("state_transition", "状态测试"),
    ("permission", "权限测试"),
    ("data_consistency", "数据一致性"),
    ("security", "安全测试"),
    ("performance", "性能测试"),
    ("compatibility", "兼容性测试"),
    ("usability", "可用性测试"),
    ("other", "其他"),
]

TEST_POINT_PRIORITY_CHOICES = [
    ("P0", "P0"),
    ("P1", "P1"),
    ("P2", "P2"),
]

DESIGN_METHOD_CHOICES = [
    ("equivalence_partitioning", "等价类"),
    ("boundary_value", "边界值"),
    ("scenario", "场景法"),
    ("state_transition", "状态迁移"),
    ("other", "其他"),
]

PRIORITY_CHOICES = [
    ("P0", "P0"),
    ("P1", "P1"),
    ("P2", "P2"),
    ("P3", "P3"),
]


class TestPoint(models.Model):
    """AI 生成的测试点。"""

    __test__ = False  # 避免 pytest 误收集

    requirement = models.ForeignKey(
        "requirements.Requirement",
        on_delete=models.CASCADE,
        related_name="test_points",
    )
    title = models.CharField("测试点标题", max_length=255)
    description = models.TextField("测试点描述", blank=True, default="")
    category = models.CharField("测试维度", max_length=32, choices=TEST_POINT_CATEGORY_CHOICES)
    priority = models.CharField("优先级", max_length=8, choices=TEST_POINT_PRIORITY_CHOICES, default="P1")
    design_method = models.CharField("测试设计方法", max_length=32, choices=DESIGN_METHOD_CHOICES, default="other")
    selected = models.BooleanField("是否选中", default=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        verbose_name = "测试点"
        verbose_name_plural = "测试点"
        ordering = ["id"]

    def __str__(self):
        return self.title[:50]


class TestCase(models.Model):
    """结构化测试用例（完整业务数据保存在 MySQL）。"""

    __test__ = False  # 避免 pytest 误收集

    requirement = models.ForeignKey(
        "requirements.Requirement",
        on_delete=models.CASCADE,
        related_name="test_cases",
    )
    test_point = models.ForeignKey(
        TestPoint,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="test_cases",
    )
    case_id = models.CharField("用例编号", max_length=64)
    module = models.CharField("所属模块", max_length=255, blank=True, default="")
    title = models.CharField("用例标题", max_length=500)
    preconditions = models.JSONField("前置条件", default=list, blank=True)
    steps = models.JSONField("测试步骤", default=list, blank=True)
    test_data = models.TextField("测试数据", blank=True, default="")
    expected_result = models.TextField("预期结果")
    test_type = models.CharField("类型", max_length=32, choices=CATEGORY_CHOICES)
    priority = models.CharField("优先级", max_length=8, choices=PRIORITY_CHOICES)
    design_method = models.CharField("测试设计方法", max_length=32, choices=DESIGN_METHOD_CHOICES)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        verbose_name = "测试用例"
        verbose_name_plural = "测试用例"
        ordering = ["id"]
        indexes = [
            models.Index(fields=["requirement", "test_type"]),
            models.Index(fields=["requirement", "priority"]),
            models.Index(fields=["requirement", "design_method"]),
        ]

    def __str__(self):
        return f"{self.case_id} {self.title}"


class GenerationRecord(models.Model):
    """一次 AI 生成任务的记录（状态、耗时、错误、评审结果）。"""

    STATUS_CHOICES = [
        ("running", "运行中"),
        ("success", "成功"),
        ("failed", "失败"),
    ]

    requirement = models.ForeignKey(
        "requirements.Requirement",
        on_delete=models.CASCADE,
        related_name="generation_records",
    )
    status = models.CharField("状态", max_length=32, choices=STATUS_CHOICES, default="running")
    model = models.CharField("使用模型", max_length=64, blank=True, default="")
    error_message = models.TextField("错误信息", blank=True, default="")
    duration_ms = models.IntegerField("耗时(毫秒)", default=0)
    review_result = models.JSONField("评审结果", null=True, blank=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        verbose_name = "生成记录"
        verbose_name_plural = "生成记录"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.requirement_id} - {self.status} - {self.created_at}"
