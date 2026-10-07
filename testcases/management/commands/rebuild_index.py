"""重建向量索引：将所有已保存的测试用例重新向量化并写入向量库。

使用场景：
- 切换了 Embedding 提供方 / 向量维度
- 从 Milvus 切回内存库，或首次部署后回填历史数据
- 内存向量库因进程重启丢失数据后重建
"""
from django.core.management.base import BaseCommand

from core.embeddings import get_embedding_client
from testcases.models import TestCase
from vectorstore import get_vector_store


class Command(BaseCommand):
    help = "重建测试用例向量索引"

    def handle(self, *args, **options):
        store = get_vector_store()
        embedding = get_embedding_client()
        self.stdout.write(f"向量库可用：{store.is_available()}，维度：{embedding.dimension}")

        testcases = list(TestCase.objects.select_related("requirement").all())
        if not testcases:
            self.stdout.write("没有可重建的测试用例。")
            return

        texts = []
        items = []
        for tc in testcases:
            steps = tc.steps if isinstance(tc.steps, list) else []
            text = " ".join([tc.title, " ".join(steps), tc.expected_result or ""])
            texts.append(text)

        vectors = embedding.embed(texts)
        for tc, vector in zip(testcases, vectors):
            items.append(
                {
                    "id": str(tc.pk),
                    "vector": vector,
                    "payload": {
                        "testcase_id": tc.case_id,
                        "requirement_id": tc.requirement_id,
                    },
                }
            )

        store.insert(items)
        self.stdout.write(self.style.SUCCESS(f"成功重建 {len(items)} 条向量。"))
