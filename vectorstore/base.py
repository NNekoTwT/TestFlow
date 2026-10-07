"""向量库抽象接口。

MySQL 保存完整业务数据（测试用例全文、字段等）；
向量库只负责保存向量 + 少量索引字段，用于语义相似度检索。
"""
from abc import ABC, abstractmethod


class VectorStore(ABC):
    """向量库统一接口。"""

    @abstractmethod
    def is_available(self) -> bool:
        """当前向量库是否可用。"""

    @abstractmethod
    def insert(self, items):
        """批量写入向量。

        items: list[dict]，每项结构：
            {"id": <业务主键 str>, "vector": list[float], "payload": dict}
        payload 建议包含 {"testcase_id": str, "requirement_id": int}。
        """

    @abstractmethod
    def search(self, vector, top_k=5):
        """相似度检索。

        返回 list[dict]：{"id": str, "score": float, "payload": dict}
        按相似度从高到低排序。
        """

    def delete_by_requirement(self, requirement_id):
        """删除指定需求下的所有向量（可选实现，默认 no-op）。

        用于重新生成用例前清理旧索引，避免污染相似检索。
        """

    def close(self):
        """释放连接（可选实现）。"""
