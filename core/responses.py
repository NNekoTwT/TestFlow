"""API 统一返回格式辅助函数。"""
from rest_framework.response import Response


def ok(data=None, message="ok"):
    """成功响应：code=0。"""
    return Response({"code": 0, "message": message, "data": data})


def fail(status, message, data=None):
    """失败响应：code=HTTP 状态码。"""
    return Response({"code": status, "message": message, "data": data}, status=status)
