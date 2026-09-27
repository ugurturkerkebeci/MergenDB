import os
import unittest
import tempfile
import shutil
import mergendb
from mergendb import Schema, ColumnDef, DataType
from mergendb.core.bloom import BlockBloomFilter
from mergendb.storage.reader import FileReader

class TestBloomFilter(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.tbl_path = os.path.join(self.temp_dir, "bloom_test.mgdb")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_bloom_filter_unit(self):
        bf = BlockBloomFilter()
        bf.add("alice@example.com")
        bf.add("bob@example.com")
        bf.add(12345)

        # Added elements MUST return True (Zero false negatives)
        self.assertTrue(bf.contains("alice@example.com"))
        self.assertTrue(bf.contains("bob@example.com"))
        self.assertTrue(bf.contains(12345))

        # Definitely absent element
        self.assertFalse(bf.contains("not_in_filter@unknown.com"))
        self.assertFalse(bf.contains(9999999))

        # Serialization roundtrip
        hex_val = bf.to_hex()
        bf2 = BlockBloomFilter.from_hex(hex_val)
        self.assertIsNotNone(bf2)
        self.assertTrue(bf2.contains("alice@example.com"))
        self.assertFalse(bf2.contains("not_in_filter@unknown.com"))

    def test_block_level_text_uuid_pruning(self):
        """
        Tests that Bloom Filter prunes blocks where ZoneMap min/max cannot prune.
        In each block, we intentionally put a word starting with 'a' and 'z'
        so ZoneMap min is always 'a...' and max is always 'z...'.
        Only Block 5 contains the target email 'needle@mergendb.io'.
        """
        schema = Schema([
            ColumnDef("id", DataType.INT64),
            ColumnDef("email", DataType.STRING),
            ColumnDef("data", DataType.STRING)
        ])

        # 10 blocks of 50 rows each = 500 rows
        table = mergendb.create_table(self.tbl_path, schema, block_size=50)
        rows = []
        for blk in range(10):
            # First row starts with 'a', last row starts with 'z' -> ZoneMap covers ['a', 'z']
            rows.append({"id": blk * 50, "email": "a_start@domain.com", "data": "pad"})
            for r in range(1, 49):
                email = f"user_{blk}_{r}@domain.com"
                if blk == 5 and r == 25:
                    email = "needle@mergendb.io"
                rows.append({"id": blk * 50 + r, "email": email, "data": "pad"})
            rows.append({"id": blk * 50 + 49, "email": "z_end@domain.com", "data": "pad"})

        table.insert(rows, block_size=50)

        with FileReader(self.tbl_path) as reader:
            self.assertEqual(len(reader.blocks), 10)

            # Check that every single block has min starting with 'a' and max starting with 'z'
            for blk in reader.blocks:
                zm = blk.columns["email"].zone_map
                self.assertEqual(zm.min_value, "a_start@domain.com")
                self.assertEqual(zm.max_value, "z_end@domain.com")
                # ZoneMap alone CANNOT prune "needle@mergendb.io" because 'a' <= 'needle' <= 'z'
                self.assertFalse(zm.can_prune("==", "needle@mergendb.io"))

                # BUT Bloom Filter CAN prune in all blocks except block 5!
                if blk.block_id == 5:
                    self.assertFalse(blk.columns["email"].can_prune("==", "needle@mergendb.io"))
                else:
                    self.assertTrue(blk.columns["email"].can_prune("==", "needle@mergendb.io"))

            # Now run scan with predicate:
            scanned_batches = []
            for batch, stats in reader.scan(
                columns=["id", "email"],
                predicates=[("email", "==", "needle@mergendb.io")],
                parallel=False
            ):
                scanned_batches.append(batch)

            # Exactly 9 blocks were skipped, exactly 1 block was scanned!
            self.assertEqual(stats.blocks_skipped, 9)
            self.assertEqual(stats.blocks_scanned, 1)

            # Query engine verification
            res = mergendb.query(f'FROM "{self.tbl_path}" | WHERE email = "needle@mergendb.io" | SELECT id, email')
            self.assertEqual(len(res.rows), 1)
            self.assertEqual(res.rows[0][1], "needle@mergendb.io")

if __name__ == "__main__":
    unittest.main()
