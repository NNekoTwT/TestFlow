"""测试专用 settings：使用 SQLite 内存库，避免依赖 MySQL。

自动化测试通过 pytest.ini 指定 DJANGO_SETTINGS_MODULE=config.settings_test 加载此文件。
"""
from .settings import *  # noqa: F401,F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# 测试环境不配置真实 API Key，LLM 相关用例通过 Mock 覆盖
DEEPSEEK_API_KEY = ""
