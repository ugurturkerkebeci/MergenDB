import unittest
import os
import shutil
import tempfile
from mergendb import MergenDB, Schema, ColumnDef, DataType, Table

class TestVectorV1(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.table_path = os.path.join(self.test_dir, "vectors.mgdb")

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_vector_creation_and_search(self):
        schema = Schema([
            ColumnDef("doc_id", DataType.INT32),
            ColumnDef("topic", DataType.STRING),
            ColumnDef("embedding", DataType.VECTOR)
        ])
        table = Table.create(self.table_path, schema, block_size=10)

        rows = [
            {"doc_id": 1, "topic": "AI", "embedding": [1.0, 0.0, 0.0]},
            {"doc_id": 2, "topic": "Cooking", "embedding": [0.0, 1.0, 0.0]},
            {"doc_id": 3, "topic": "Robotics", "embedding": [0.95, 0.05, 0.0]},
            {"doc_id": 4, "topic": "Baking", "embedding": [0.05, 0.95, 0.0]},
            {"doc_id": 5, "topic": "AI Ethics", "embedding": [0.8, 0.2, 0.0]},
        ]
        table.insert(rows)
        self.assertEqual(len(table), 5)

        # 1. Cosine Vector Search
        res = table.vector_search("embedding", [1.0, 0.0, 0.0], top_k=2, metric="cosine")
        self.assertEqual(len(res), 2)
        top1 = res[0]
        # Topic should be AI
        topic_idx = res.column_names.index("topic")
        self.assertEqual(top1[topic_idx], "AI")

        # 2. Hybrid Search (Filter + Vector Search)
        res_hybrid = table.vector_search("embedding", [1.0, 0.0, 0.0], top_k=5, filter="topic == 'Robotics'")
        self.assertEqual(len(res_hybrid), 1)
        self.assertEqual(res_hybrid[0][topic_idx], "Robotics")

        # 3. L2 Euclidean Distance
        res_l2 = table.vector_search("embedding", [1.0, 0.0, 0.0], top_k=2, metric="l2")
        self.assertEqual(len(res_l2), 2)
        self.assertEqual(res_l2[0][topic_idx], "AI")

        # 4. SQL with Vector Similarity Function
        clean_path = self.table_path.replace("\\", "/")
        sql = f"SELECT doc_id, topic, cosine_similarity(embedding, [1.0, 0.0, 0.0]) AS score FROM \"{clean_path}\" ORDER BY score DESC LIMIT 3"
        sql_res = MergenDB.query(sql)
        self.assertEqual(len(sql_res), 3)
        self.assertEqual(sql_res[0][1], "AI")

if __name__ == "__main__":
    unittest.main()
