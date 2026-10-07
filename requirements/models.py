from django.db import models


class Requirement(models.Model):
    """软件功能需求。"""

    title = models.CharField("需求标题", max_length=255)
    module = models.CharField("所属模块", max_length=255, blank=True, default="")
    description = models.TextField("需求描述")
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "需求"
        verbose_name_plural = "需求"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
