"""Embedding 客户端：把文本向量化，供向量检索使用。

默认使用内置的字符 n-gram 哈希向量（离线可用、确定性、无需外部 API），
保证项目在没有额外 Embedding 服务时也能完整运行。
如需真实语义向量，可将 EMBEDDING_PROVIDER 设为 sentence_transformers
（需要额外 `pip install sentence-transformers`）。
"""
import hashlib
import logging
import math
import re

from django.conf import settings

logger = logging.getLogger("testflow")


class EmbeddingClient:
    """向量化客户端接口。"""

    @property
    def dimension(self) -> int:
        raise NotImplementedError

    def embed(self, texts):
        """批量向量化，返回 list[list[float]]。"""
        raise NotImplementedError

    def embed_one(self, text):
        return self.embed([text])[0]


class HashEmbedding(EmbeddingClient):
    """基于特征哈希（Feature Hashing）的确定性向量。

    对字符 2/3/4-gram 做 MD5 哈希并带符号累加到固定维度向量，
    相同/相似文本会得到相近的向量，可用于轻量语义相似度检索。
    这不是真实语义模型，仅作为开箱即用的默认实现。
    """

    def __init__(self, dimension=None):
        self._dimension = dimension or settings.EMBEDDING_DIMENSION

    @property
    def dimension(self):
        return self._dimension

    def embed(self, texts):
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text):
        text = re.sub(r"\s+", " ", (text or "").lower()).strip()
        vec = [0.0] * self._dimension
        for n in (2, 3, 4):
            for i in range(len(text) - n + 1):
                gram = text[i : i + n]
                digest = hashlib.md5(gram.encode("utf-8")).digest()
                idx = int.from_bytes(digest[:4], "big") % self._dimension
                sign = 1 if digest[4] & 1 else -1
                vec[idx] += sign
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


def _sentence_transformer_embedding():
    """懒加载 sentence-transformers（可选依赖）。"""
    from sentence_transformers import SentenceTransformer

    model_name = getattr(settings, "EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")

    class _STEmbedding(EmbeddingClient):
        def __init__(self):
            self._model = SentenceTransformer(model_name)
            self._dimension = self._model.get_sentence_embedding_dimension()

        @property
        def dimension(self):
            return self._dimension

        def embed(self, texts):
            return self._model.encode(list(texts), normalize_embeddings=True).tolist()

    return _STEmbedding()


def get_embedding_client():
    """根据配置返回 EmbeddingClient 实例。"""
    provider = settings.EMBEDDING_PROVIDER
    if provider == "sentence_transformers":
        try:
            return _sentence_transformer_embedding()
        except Exception as exc:  # 依赖缺失或模型下载失败
            logger.warning("sentence_transformers 初始化失败（%s），回退到内置 hash 向量", exc)
    return HashEmbedding()
