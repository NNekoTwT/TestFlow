"""AI Service 的公共辅助函数。"""
import json

from langchain_core.messages import HumanMessage, SystemMessage

from core.llm import invoke_json


def call_with_schema(llm, system_prompt, user_prompt):
    """构建 messages 并调用 LLM，返回解析后的 dict。"""
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]
    return invoke_json(llm, messages)


def schema_json(model_cls):
    """将 Pydantic 模型的 JSON Schema 序列化为字符串，注入 Prompt。"""
    return json.dumps(model_cls.model_json_schema(), ensure_ascii=False, indent=2)
