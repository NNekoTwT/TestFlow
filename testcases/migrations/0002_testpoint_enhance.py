# 扩充测试点：content -> title + description，新增 priority / selected，丰富分类维度。

from django.db import migrations, models


def copy_content_to_title_description(apps, schema_editor):
    """把旧字段 content 的内容回填到 title / description（无旧数据时为空操作）。"""
    TestPoint = apps.get_model("testcases", "TestPoint")
    for tp in TestPoint.objects.only("content").all():
        content = tp.content or ""
        tp.title = content[:255]
        tp.description = content
        tp.save(update_fields=["title", "description"])


class Migration(migrations.Migration):

    dependencies = [
        ("testcases", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="testpoint",
            name="title",
            field=models.CharField(default="", max_length=255, verbose_name="测试点标题"),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="testpoint",
            name="description",
            field=models.TextField(blank=True, default="", verbose_name="测试点描述"),
        ),
        migrations.AddField(
            model_name="testpoint",
            name="priority",
            field=models.CharField(
                choices=[("P0", "P0"), ("P1", "P1"), ("P2", "P2")],
                default="P1",
                max_length=8,
                verbose_name="优先级",
            ),
        ),
        migrations.AddField(
            model_name="testpoint",
            name="selected",
            field=models.BooleanField(default=True, verbose_name="是否选中"),
        ),
        migrations.RunPython(copy_content_to_title_description, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="testpoint",
            name="content",
        ),
        migrations.AlterField(
            model_name="testpoint",
            name="category",
            field=models.CharField(
                choices=[
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
                ],
                max_length=32,
                verbose_name="测试维度",
            ),
        ),
        migrations.AlterField(
            model_name="testpoint",
            name="design_method",
            field=models.CharField(
                choices=[
                    ("equivalence_partitioning", "等价类"),
                    ("boundary_value", "边界值"),
                    ("scenario", "场景法"),
                    ("state_transition", "状态迁移"),
                    ("other", "其他"),
                ],
                default="other",
                max_length=32,
                verbose_name="测试设计方法",
            ),
        ),
    ]
