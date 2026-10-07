"""向量库测试：内存实现检索 + Milvus 降级逻辑。"""
import numpy as np

from vectorstore import get_vector_store, reset_vector_store
from vectorstore.in_memory import InMemoryVectorStore
from vectorstore.milvus_store import MilvusVectorStore


class TestInMemoryVectorStore:
    def test_search_returns_top_k_sorted(self):
        store = InMemoryVectorStore()
        store.insert(
            [
                {"id": "a", "vector": [1.0, 0.0], "payload": {"requirement_id": 1}},
                {"id": "b", "vector": [0.9, 0.1], "payload": {"requirement_id": 1}},
                {"id": "c", "vector": [0.0, 1.0], "payload": {"requirement_id": 2}},
            ]
        )
        hits = store.search([1.0, 0.0], top_k=2)
        assert [h["id"] for h in hits] == ["a", "b"]
        assert hits[0]["score"] >= hits[1]["score"]

    def test_search_empty(self):
        store = InMemoryVectorStore()
        assert store.search([1.0, 0.0]) == []

    def test_delete_by_requirement(self):
        store = InMemoryVectorStore()
        store.insert(
            [
                {"id": "a", "vector": [1.0, 0.0], "payload": {"requirement_id": 1}},
                {"id": "b", "vector": [0.0, 1.0], "payload": {"requirement_id": 2}},
            ]
        )
        store.delete_by_requirement(1)
        hits = store.search([1.0, 0.0], top_k=10)
        assert [h["id"] for h in hits] == ["b"]


class TestMilvusDegradation:
    def test_factory_returns_in_memory_when_milvus_disabled(self, settings):
        settings.MILVUS_ENABLED = False
        reset_vector_store()
        store = get_vector_store()
        assert isinstance(store, InMemoryVectorStore)

    def test_milvus_store_unavailable_without_pymilvus(self):
        # pymilvus 是可选依赖，本机未安装时连接必然失败 -> 不可用
        store = MilvusVectorStore("localhost", 19530, "test", 256)
        assert store.is_available() is False
