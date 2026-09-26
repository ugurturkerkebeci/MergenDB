import unittest
import os
import shutil
import tempfile
import mergendb

class TestQueryEngine(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.filepath = os.path.join(self.test_dir, "iot_sensors.mgdb").replace("\\", "/")

        schema = mergendb.Schema([
            mergendb.ColumnDef("timestamp", mergendb.DataType.INT64),
            mergendb.ColumnDef("device_id", mergendb.DataType.STRING),
            mergendb.ColumnDef("room", mergendb.DataType.STRING),
            mergendb.ColumnDef("temperature", mergendb.DataType.FLOAT64),
            mergendb.ColumnDef("humidity", mergendb.DataType.FLOAT64),
            mergendb.ColumnDef("battery", mergendb.DataType.INT32)
        ])

        self.table = mergendb.create_table(self.filepath, schema, block_size=200)

        # Generate 1000 records
        rows = []
        base_time = 1700000000
        rooms = ["living_room", "kitchen", "bedroom", "garage"]
        for i in range(1000):
            rows.append({
                "timestamp": base_time + (i * 10),
                "device_id": f"dev_{i % 10}",
                "room": rooms[i % len(rooms)],
                "temperature": 18.0 + (i % 25),  # 18.0 to 42.0
                "humidity": 40.0 + (i % 30),
                "battery": 100 - (i // 20)      # 100 down to 50
            })
        self.table.insert_many(rows)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_simple_select_and_filter(self):
        q = f"""
        FROM "{self.filepath}"
        | WHERE temperature > 40.0 AND room == "kitchen"
        | SELECT device_id, room, temperature
        | LIMIT 5
        """
        res = mergendb.query(q)
        self.assertGreater(len(res), 0)
        self.assertLessEqual(len(res), 5)
        self.assertEqual(res.column_names, ["device_id", "room", "temperature"])
        for r in res.rows:
            self.assertEqual(r[1], "kitchen")
            self.assertGreater(r[2], 40.0)

    def test_compute_column(self):
        q = f"""
        FROM "{self.filepath}"
        | WHERE battery < 60
        | COMPUTE temp_f = (temperature * 1.8) + 32.0
        | SELECT room, temperature, temp_f, battery
        | LIMIT 10
        """
        res = mergendb.query(q)
        self.assertGreater(len(res), 0)
        self.assertEqual(res.column_names, ["room", "temperature", "temp_f", "battery"])
        for r in res.rows:
            temp_c = r[1]
            temp_f = r[2]
            expected_f = (temp_c * 1.8) + 32.0
            self.assertAlmostEqual(temp_f, expected_f, places=2)

    def test_aggregation_and_group_by(self):
        q = f"""
        FROM "{self.filepath}"
        | AGGREGATE count(*) AS total_readings, avg(temperature) AS avg_temp, max(temperature) AS max_temp BY room
        | SORT total_readings DESC
        """
        res = mergendb.query(q)
        self.assertEqual(len(res), 4) # 4 rooms
        self.assertIn("room", res.column_names)
        self.assertIn("avg_temp", res.column_names)
        # Each room should have 250 readings (1000 / 4)
        for r in res.rows:
            self.assertEqual(r[1], 250)

    def test_sort_desc(self):
        q = f"""
        FROM "{self.filepath}"
        | SELECT timestamp, battery
        | SORT battery DESC
        | LIMIT 3
        """
        res = mergendb.query(q)
        self.assertEqual(len(res), 3)
        self.assertEqual(res.rows[0][1], 100) # Max battery is 100

    def test_like_and_advanced_aggregates(self):
        # 1. LIKE pattern test
        q1 = f"""
        FROM "{self.filepath}"
        | WHERE room LIKE "kit%"
        | SELECT room, device_id
        | LIMIT 5
        """
        res1 = mergendb.query(q1)
        self.assertGreater(len(res1), 0)
        for r in res1.rows:
            self.assertTrue(r[0].startswith("kit"))

        # 2. Median and Stddev test
        q2 = f"""
        FROM "{self.filepath}"
        | AGGREGATE median(temperature) AS med_temp, stddev(temperature) AS sd_temp
        """
        res2 = mergendb.query(q2)
        self.assertEqual(len(res2), 1)
        self.assertIsNotNone(res2.rows[0][0])
        self.assertGreater(res2.rows[0][1], 0.0)

if __name__ == "__main__":
    unittest.main()
