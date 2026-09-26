import zlib
from typing import List, Any, Tuple, Optional
from mergendb.core.types import DataType, is_numeric
from mergendb.core.block import ZoneMap
from mergendb.compression.encodings import (
    EncodingType,
    encode_raw,
    decode_raw,
    encode_rle,
    decode_rle,
    encode_dict,
    decode_dict,
    encode_delta,
    decode_delta,
    encode_bitpacked_bool,
    decode_bitpacked_bool
)

def compute_zone_map(values: List[Any]) -> ZoneMap:
    """Calculates min, max, null_count, and total count for a vector of values."""
    if not values:
        return ZoneMap(min_value=None, max_value=None, null_count=0, count=0)

    non_nulls = [v for v in values if v is not None]
    null_count = len(values) - len(non_nulls)

    if not non_nulls:
        return ZoneMap(min_value=None, max_value=None, null_count=null_count, count=len(values))

    try:
        min_v = min(non_nulls)
        max_v = max(non_nulls)
    except TypeError:
        min_v = None
        max_v = None

    return ZoneMap(
        min_value=min_v,
        max_value=max_v,
        null_count=null_count,
        count=len(values)
    )

class ColumnCompressor:
    """
    Intelligent adaptive compressor that samples or evaluates candidates
    and selects the encoding yielding the smallest footprint.
    """

    @classmethod
    def compress(cls, values: List[Any], dtype: DataType, apply_zlib: bool = True) -> Tuple[bytes, EncodingType, ZoneMap, int]:
        zone_map = compute_zone_map(values)

        # Baseline uncompressed raw representation
        raw_bytes = encode_raw(values, dtype)
        uncompressed_size = len(raw_bytes)

        if len(values) == 0:
            return raw_bytes, EncodingType.RAW, zone_map, 0

        best_bytes = raw_bytes
        best_enc = EncodingType.RAW

        if dtype == DataType.BOOL:
            packed_bytes = encode_bitpacked_bool(values)
            if len(packed_bytes) < len(best_bytes):
                best_bytes = packed_bytes
                best_enc = EncodingType.BIT_PACKED_BOOL

        elif dtype in (DataType.INT32, DataType.INT64, DataType.TIMESTAMP):
            # Check Delta / FoR
            try:
                delta_bytes = encode_delta(values, dtype)
                if len(delta_bytes) < len(best_bytes):
                    best_bytes = delta_bytes
                    best_enc = EncodingType.DELTA
            except Exception:
                pass

            # Check RLE
            try:
                rle_bytes = encode_rle(values, dtype)
                if len(rle_bytes) < len(best_bytes):
                    best_bytes = rle_bytes
                    best_enc = EncodingType.RLE
            except Exception:
                pass

        elif dtype == DataType.STRING:
            # Check Dictionary encoding
            try:
                unique_ratio = len(set(values)) / len(values) if values else 1.0
                if unique_ratio < 0.6:  # Good candidate for dictionary
                    dict_bytes = encode_dict(values, dtype)
                    if len(dict_bytes) < len(best_bytes):
                        best_bytes = dict_bytes
                        best_enc = EncodingType.DICTIONARY
            except Exception:
                pass

            # Check RLE
            try:
                rle_bytes = encode_rle(values, dtype)
                if len(rle_bytes) < len(best_bytes):
                    best_bytes = rle_bytes
                    best_enc = EncodingType.RLE
            except Exception:
                pass

        # Optional lightweight secondary compression with zlib if it saves > 10%
        if apply_zlib and len(best_bytes) > 64:
            z_compressed = zlib.compress(best_bytes, level=3) # level 3: fast & good ratio
            if len(z_compressed) + 1 < len(best_bytes):
                # Prefix with 0x01 flag indicating zlib compressed
                final_bytes = b"\x01" + z_compressed
            else:
                final_bytes = b"\x00" + best_bytes
        else:
            final_bytes = b"\x00" + best_bytes

        return final_bytes, best_enc, zone_map, uncompressed_size

    @classmethod
    def decompress(cls, data: bytes, enc_type: EncodingType, dtype: DataType) -> List[Any]:
        if not data:
            return []

        # Check if secondary zlib compression was applied
        is_zlib = (data[0] == 1)
        payload = data[1:]

        if is_zlib:
            payload = zlib.decompress(payload)

        if enc_type == EncodingType.RAW:
            return decode_raw(payload, dtype)
        elif enc_type == EncodingType.BIT_PACKED_BOOL:
            return decode_bitpacked_bool(payload)
        elif enc_type == EncodingType.DELTA:
            return decode_delta(payload, dtype)
        elif enc_type == EncodingType.RLE:
            return decode_rle(payload, dtype)
        elif enc_type == EncodingType.DICTIONARY:
            return decode_dict(payload, dtype)
        else:
            raise ValueError(f"Unknown encoding type: {enc_type}")
