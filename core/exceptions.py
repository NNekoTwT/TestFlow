"""统一异常定义与 DRF 异常处理器。

目标：API 返回统一结构 {"code": <int>, "message": <str>, "data": <any>}，
其中 code=0 表示成功，code>0 表示失败（使用 HTTP 状态码）。
"""
import logging

from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger("testflow")


class AppError(Exception):
    """业务异常基类。所有可预期的错误都应继承此类。"""

    status_code = 500
    default_message = "服务器内部错误"

    def __init__(self, message=None, status_code=None):
        self.message = message or self.default_message
        self.status_code = status_code or self.status_code
        super().__init__(self.message)


class BadRequestError(AppError):
    status_code = 400
    default_message = "请求参数错误"


class NotFoundError(AppError):
    status_code = 404
    default_message = "资源不存在"


class LLMConfigError(AppError):
    status_code = 503
    default_message = "LLM 未正确配置"


class LLMError(AppError):
    status_code = 502
    default_message = "LLM 调用失败"


class LLMJSONParseError(AppError):
    status_code = 502
    default_message = "LLM 输出解析失败"


class VectorStoreError(AppError):
    status_code = 503
    default_message = "向量库不可用"


class ExportError(AppError):
    status_code = 500
    default_message = "导出失败"


def _format_detail(detail):
    """把 DRF 的校验错误 detail 转成可读字符串。"""
    if isinstance(detail, str):
        return detail
    if isinstance(detail, dict):
        return "; ".join(
            f"{key}: {_format_detail(value)}" for key, value in detail.items()
        )
    if isinstance(detail, (list, tuple)):
        return "; ".join(_format_detail(item) for item in detail)
    return str(detail)


def api_exception_handler(exc, context):
    """统一 API 异常处理。"""
    # 1) 业务异常：直接返回统一格式
    if isinstance(exc, AppError):
        return Response(
            {"code": exc.status_code, "message": exc.message, "data": None},
            status=exc.status_code,
        )

    # 2) DRF 内置异常（如参数校验、404 等）
    response = drf_exception_handler(exc, context)
    if response is not None:
        detail = response.data.get("detail", response.data) if isinstance(response.data, dict) else response.data
        return Response(
            {"code": response.status_code, "message": _format_detail(detail), "data": None},
            status=response.status_code,
        )

    # 3) 未预期异常：记录日志，避免吞异常
    logger.exception("未处理的服务器异常：%s", exc)
    return Response(
        {"code": 500, "message": "服务器内部错误", "data": None},
        status=500,
    )
