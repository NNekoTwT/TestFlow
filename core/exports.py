"""测试用例导出：Excel / Markdown。"""
import io
import logging
import re

import pandas as pd

from .exceptions import ExportError

logger = logging.getLogger("testflow")

_NUMBER_PREFIX = re.compile(r"^\s*\d+[.、)）]\s*")


def _strip_numbering(text):
    """去掉 LLM 可能自带的序号前缀（如「1. 」「2、」），避免双重编号。"""
    return _NUMBER_PREFIX.sub("", str(text)).strip()


def _humanize(items):
    """把 list 类型的步骤 / 前置条件转换为人类可读的多行文本。"""
    if items is None:
        return ""
    if isinstance(items, str):
        return items
    if isinstance(items, (list, tuple)):
        return "\n".join(f"{i}. {_strip_numbering(item)}" for i, item in enumerate(items, 1))
    return str(items)


def _to_rows(testcases):
    rows = []
    for tc in testcases:
        rows.append(
            {
                "用例编号": tc.case_id,
                "模块": tc.module or "",
                "测试标题": tc.title,
                "前置条件": _humanize(tc.preconditions),
                "测试步骤": _humanize(tc.steps),
                "测试数据": tc.test_data or "",
                "预期结果": tc.expected_result or "",
                "类型": tc.test_type,
                "优先级": tc.priority,
                "测试设计方法": tc.design_method,
            }
        )
    return rows


def export_excel(testcases):
    """将测试用例列表导出为 Excel 字节流。"""
    try:
        df = pd.DataFrame(_to_rows(testcases))
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="测试用例")
        return buf.getvalue()
    except Exception as exc:
        raise ExportError(f"Excel 导出失败：{exc}") from exc


def export_markdown(requirement, testcases):
    """将测试用例列表导出为 Markdown 文本。"""
    lines = [
        f"# 测试用例：{requirement.title}",
        "",
        f"- 所属模块：{requirement.module or '-'}",
        f"- 用例总数：{len(testcases)}",
        "",
        "| 用例编号 | 标题 | 类型 | 优先级 | 设计方法 | 前置条件 | 步骤 | 预期结果 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for tc in testcases:
        pre = _humanize(tc.preconditions).replace("\n", "<br>")
        steps = _humanize(tc.steps).replace("\n", "<br>")
        expected = (tc.expected_result or "").replace("\n", "<br>")
        lines.append(
            f"| {tc.case_id} | {tc.title} | {tc.test_type} | {tc.priority} | "
            f"{tc.design_method} | {pre} | {steps} | {expected} |"
        )
    return "\n".join(lines)
