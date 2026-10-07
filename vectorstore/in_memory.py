"""内存向量库：作为 Milvus 不可用时的降级实现。

仅保存向量与索引字段，进程重启后数据丢失（完整数据仍在 MySQL）。
使用余弦相似度做检索，保证项目在没有任何外部向量服务时也能完整运行。
"""
import logging

import numpy as np

from .base import VectorStore

logger = logging.getLogger("testflow")


class InMemoryVectorStore(VectorStore):
    def __init__(self):
        self._ids = []
        self._vectors = []
        self._payloads = []

    def is_available(self):
        return True

    def insert(self, items):
        for item in items:
            self._ids.append(str(item["id"]))
            self._vectors.append(item["vector"])
            self._payloads.append(item.get("payload") or {})

    def search(self, vector, top_k=5):
        if not self._ids:
            return []

        matrix = np.asarray(self._vectors, dtype=np.float64)
        query = np.asarray(vector, dtype=np.float64)

        # 余弦相似度
        norms = np.linalg.norm(matrix, axis=1) * (np.linalg.norm(query) + 1e-9)
        sims = (matrix @ query) / np.maximum(norms, 1e-9)

        order = np.argsort(-sims)[:top_k]
        results = []
        for i in order:
            results.append(
                {
                    "id": self._ids[i],
                    "score": float(sims[i]),
                    "payload": self._payloads[i],
                }
            )
        return results

    def delete_by_requirement(self, requirement_id):
        keep_ids, keep_vectors, keep_payloads = [], [], []
        for i, payload in enumerate(self._payloads):
            if str(payload.get("requirement_id")) == str(requirement_id):
                continue
            keep_ids.append(self._ids[i])
            keep_vectors.append(self._vectors[i])
            keep_payloads.append(payload)
        self._ids = keep_ids
        self._vectors = keep_vectors
        self._payloads = keep_payloads

    def close(self):
        self._ids = []
        self._vectors = []
        self._payloads = []
