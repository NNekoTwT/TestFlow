"""LLM 客户端：封装 DeepSeek 调用与结构化 JSON 解析。

通过 LangChain 的 ChatOpenAI 指向 DeepSeek 的 OpenAI 兼容接口，
配合 response_format=json_object 让模型直接输出 JSON，再交给 Pydantic 校验。
"""
import json
import logging
import re

from django.conf import settings
from langchain_openai import ChatOpenAI

from .exceptions import LLMConfigError, LLMError, LLMJSONParseError

logger = logging.getLogger("testflow.ai")


def build_llm(temperature=0.1):
    """根据配置构建 LangChain ChatOpenAI（指向 DeepSeek）。

    :raises LLMConfigError: 未配置 DEEPSEEK_API_KEY 时抛出。
    """
    api_key = settings.DEEPSEEK_API_KEY
    if not api_key:
        raise LLMConfigError(
            "DEEPSEEK_API_KEY 未配置，请在 .env 中设置后重试"
        )

    return ChatOpenAI(
        model=settings.DEEPSEEK_MODEL,
        api_key=api_key,
        base_url=settings.DEEPSEEK_BASE_URL,
        temperature=temperature,
        timeout=settings.DEEPSEEK_TIMEOUT,
        max_retries=settings.DEEPSEEK_MAX_RETRIES,
        # DeepSeek 支持 OpenAI 兼容的 JSON 模式
        model_kwargs={"response_format": {"type": "json_object"}},
    )


def extract_json(text):
    """从 LLM 输出中稳健地提取 JSON 对象。

    处理常见情况：直接 JSON、被 Markdown 代码块包裹、前后带多余文字。
    :raises LLMJSONParseError: 无法解析时抛出。
    """
    if not text:
        raise LLMJSONParseError("LLM 返回了空内容")

    text = text.strip()

    # 去掉 Markdown 代码块围栏
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 兜底：截取第一个 { 到最后一个 }
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise LLMJSONParseError(f"LLM 输出中未找到合法 JSON：{text[:200]}")

    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        raise LLMJSONParseError(f"LLM 输出 JSON 解析失败：{exc}") from exc


def invoke_json(llm, messages):
    """调用 LLM 并返回解析后的 dict。

    :raises LLMError: 网络 / 超时 / 鉴权等调用失败。
    :raises LLMJSONParseError: 输出无法解析为 JSON。
    """
    try:
        response = llm.invoke(messages)
    except Exception as exc:
        raise LLMError(f"DeepSeek API 调用失败：{exc}") from exc

    content = response.content
    # 部分实现返回 content blocks 列表
    if isinstance(content, list):
        content = "".join(getattr(block, "text", str(block)) for block in content)

    return extract_json(content)
