"""向量库工厂：按配置选择 Milvus 或内存降级实现。

单例缓存保证同一进程内（尤其是内存向量库）共享同一份索引数据。
"""
import logging

from django.conf import settings

from .base import VectorStore
from .in_memory import InMemoryVectorStore
from .milvus_store import MilvusVectorStore

logger = logging.getLogger("testflow")

_store = None


def get_vector_store() -> VectorStore:
    """返回向量库单例。

    优先 Milvus；若未启用或不可用，则降级到内存实现，保证核心流程可用。
    """
    global _store
    if _store is not None:
        return _store

    if settings.MILVUS_ENABLED:
        store = MilvusVectorStore(
            host=settings.MILVUS_HOST,
            port=settings.MILVUS_PORT,
            collection_name=settings.MILVUS_COLLECTION,
            dimension=settings.EMBEDDING_DIMENSION,
        )
        if store.is_available():
            _store = store
            return _store
        logger.warning("Milvus 未启用或不可用，降级到内存向量库")

    _store = InMemoryVectorStore()
    return _store


def reset_vector_store():
    """重置单例（供测试使用）。"""
    global _store
    if _store is not None:
        try:
            _store.close()
        except Exception:
            pass
    _store = None
