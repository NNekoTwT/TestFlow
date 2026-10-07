"""Milvus 向量库实现（可选）。

通过 pymilvus 的 MilvusClient 连接独立部署的 Milvus（见 docker-compose.yml）。
Milvus 只保存向量 + 少量索引字段（entity_id / requirement_id），
完整业务数据始终以 MySQL 为准。

设计要点：任何连接失败都只把 store 标记为不可用，由上层降级到内存向量库，
保证核心 AI 生成流程不受 Milvus 状态影响。
"""
import logging

from .base import VectorStore

logger = logging.getLogger("testflow")

# Milvus 集合字段
FIELD_ID = "id"                    # 自动主键
FIELD_VECTOR = "vector"            # 向量字段
FIELD_ENTITY_ID = "entity_id"      # 业务唯一键（对应 MySQL 中 TestCase.pk）
FIELD_REQUIREMENT_ID = "requirement_id"


class MilvusVectorStore(VectorStore):
    def __init__(self, host, port, collection_name, dimension):
        self._host = host
        self._port = port
        self._collection_name = collection_name
        self._dimension = dimension
        self._client = None
        self._available = False
        self._connect()

    def _connect(self):
        try:
            from pymilvus import DataType, MilvusClient  # 延迟导入，避免强依赖

            uri = f"http://{self._host}:{self._port}"
            self._client = MilvusClient(uri=uri)

            if not self._client.has_collection(self._collection_name):
                self._create_collection()
            self._available = True
            logger.info("Milvus 连接成功：%s / 集合 %s", uri, self._collection_name)
        except Exception as exc:  # pymilvus 未安装 / 服务不可达等
            self._available = False
            logger.warning("Milvus 不可用，将降级到内存向量库：%s", exc)

    def _create_collection(self):
        """按官方 MilvusClient 快速开始方式显式创建集合与索引。"""
        from pymilvus import DataType

        schema = self._client.create_schema(auto_id=True, enable_dynamic_field=False)
        schema.add_field(field_name=FIELD_ID, datatype=DataType.INT64, is_primary=True)
        schema.add_field(field_name=FIELD_VECTOR, datatype=DataType.FLOAT_VECTOR, dim=self._dimension)
        schema.add_field(field_name=FIELD_ENTITY_ID, datatype=DataType.VARCHAR, max_length=64)
        schema.add_field(field_name=FIELD_REQUIREMENT_ID, datatype=DataType.INT64)

        index_params = self._client.prepare_index_params()
        index_params.add_index(field_name=FIELD_VECTOR, index_type="AUTOINDEX", metric_type="COSINE")

        self._client.create_collection(
            collection_name=self._collection_name,
            schema=schema,
            index_params=index_params,
        )

    def is_available(self):
        return self._available

    def insert(self, items):
        if not self._available:
            return
        rows = [
            {
                FIELD_VECTOR: item["vector"],
                FIELD_ENTITY_ID: str(item["id"]),
                FIELD_REQUIREMENT_ID: int(item["payload"].get("requirement_id", 0)),
            }
            for item in items
        ]
        try:
            self._client.insert(self._collection_name, rows)
        except Exception as exc:
            logger.error("Milvus 写入失败：%s", exc)
            raise

    def search(self, vector, top_k=5):
        if not self._available:
            return []
        try:
            raw = self._client.search(
                collection_name=self._collection_name,
                data=[vector],
                limit=top_k,
                output_fields=[FIELD_ENTITY_ID, FIELD_REQUIREMENT_ID],
            )
        except Exception as exc:
            logger.error("Milvus 检索失败：%s", exc)
            raise

        results = []
        # MilvusClient.search 返回 [[hit, ...]]
        for hit in (raw[0] if raw else []):
            entity = hit.get("entity", {})
            results.append(
                {
                    "id": entity.get(FIELD_ENTITY_ID),
                    "score": float(hit.get("distance", 0.0)),
                    "payload": {"requirement_id": entity.get(FIELD_REQUIREMENT_ID)},
                }
            )
        return results

    def delete_by_requirement(self, requirement_id):
        if not self._available:
            return
        try:
            self._client.delete(
                self._collection_name,
                filter=f"{FIELD_REQUIREMENT_ID} == {int(requirement_id)}",
            )
        except Exception as exc:
            logger.error("Milvus 删除失败：%s", exc)
            raise

    def close(self):
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None
