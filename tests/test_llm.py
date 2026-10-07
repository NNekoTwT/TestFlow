"""LLM 客户端单元测试：JSON 提取与配置校验。"""
import pytest

from core.exceptions import LLMConfigError, LLMJSONParseError
from core.llm import build_llm, extract_json


class TestExtractJson:
    def test_plain_json(self):
        assert extract_json('{"a": 1}') == {"a": 1}

    def test_code_fenced_json(self):
        text = '```json\n{"a": 1}\n```'
        assert extract_json(text) == {"a": 1}

    def test_json_with_surrounding_text(self):
        text = '好的，结果如下：{"a": 1} 以上。'
        assert extract_json(text) == {"a": 1}

    def test_empty_raises(self):
        with pytest.raises(LLMJSONParseError):
            extract_json("")

    def test_no_json_raises(self):
        with pytest.raises(LLMJSONParseError):
            extract_json("没有任何 JSON")


class TestBuildLLM:
    def test_missing_key_raises(self, settings):
        settings.DEEPSEEK_API_KEY = ""
        with pytest.raises(LLMConfigError):
            build_llm()

    def test_with_key_returns_llm(self, settings):
        settings.DEEPSEEK_API_KEY = "sk-test"
        llm = build_llm()
        assert llm.model_name == settings.DEEPSEEK_MODEL
