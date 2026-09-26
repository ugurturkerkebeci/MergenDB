import unittest
from mergendb.core.types import DataType
from mergendb.compression.encodings import (
    encode_raw, decode_raw,
    encode_rle, decode_rle,
    encode_dict, decode_dict,
    encode_delta, decode_delta,
    encode_bitpacked_bool, decode_bitpacked_bool
)
from mergendb.compression.compressor import ColumnCompressor, EncodingType

class TestCompression(unittest.TestCase):
    def test_raw_int(self):
        vals = [10, 20, 30, -5, 100]
        enc = encode_raw(vals, DataType.INT32)
        dec = decode_raw(enc, DataType.INT32)
        self.assertEqual(vals, dec)

    def test_raw_string(self):
        vals = ["apple", "banana", "cherry", None, "date"]
        enc = encode_raw(vals, DataType.STRING)
        dec = decode_raw(enc, DataType.STRING)
        self.assertEqual(vals, dec)

    def test_rle(self):
        vals = ["TR"] * 50 + ["US"] * 30 + ["DE"] * 20
        enc = encode_rle(vals, DataType.STRING)
        dec = decode_rle(enc, DataType.STRING)
        self.assertEqual(vals, dec)
        # RLE should be dramatically smaller than raw
        raw_size = len(encode_raw(vals, DataType.STRING))
        self.assertLess(len(enc), raw_size / 2)

    def test_dictionary(self):
        import random
        pool = ["category_A", "category_B", "category_C", "category_D"]
        vals = [random.choice(pool) for _ in range(500)]
        enc = encode_dict(vals, DataType.STRING)
        dec = decode_dict(enc, DataType.STRING)
        self.assertEqual(vals, dec)
        raw_size = len(encode_raw(vals, DataType.STRING))
        self.assertLess(len(enc), raw_size / 3)

    def test_delta(self):
        # Monotonically increasing timestamps or IDs
        base = 1700000000
        vals = [base + i * 2 for i in range(1000)]
        enc = encode_delta(vals, DataType.INT64)
        dec = decode_delta(enc, DataType.INT64)
        self.assertEqual(vals, dec)
        # 1000 int64 in raw is 8000 bytes. With delta (max delta 1998 -> 2 bytes), it should be ~2013 bytes!
        self.assertEqual(len(enc), 2013)
        self.assertLess(len(enc), 8000 / 3)

    def test_bitpacked_bool(self):
        vals = [True, False, True, True, False, False, False, True] * 10 # 80 bools
        enc = encode_bitpacked_bool(vals)
        dec = decode_bitpacked_bool(enc)
        self.assertEqual(vals, dec)
        # 80 bools packed should take 4 bytes header + 10 bytes = 14 bytes!
        self.assertEqual(len(enc), 14)

    def test_adaptive_compressor(self):
        # Repeated categories
        vals = ["active", "active", "pending", "active", "cancelled"] * 100
        data, enc_type, zm, uncompressed_size = ColumnCompressor.compress(vals, DataType.STRING)
        decoded = ColumnCompressor.decompress(data, enc_type, DataType.STRING)
        self.assertEqual(vals, decoded)
        self.assertEqual(zm.count, 500)
        self.assertEqual(zm.null_count, 0)
        self.assertIn(enc_type, (EncodingType.DICTIONARY, EncodingType.RLE))

if __name__ == "__main__":
    unittest.main()
