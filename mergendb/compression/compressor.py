import zlib
from typing import List, Any, Tuple, Optional, Union
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
    decode_dict_indices,
    dict_predicate_pushdown,
    raw_predicate_pushdown,
    delta_predicate_pushdown,
    rle_predicate_pushdown,
    bitpacked_bool_predicate_pushdown,
    encode_delta,
    decode_delta,
    encode_bitpacked_bool,
    decode_bitpacked_bool
)

def compute_zone_map(values: List[Any]) -> ZoneMap:
    """Calculates min, max, null_count, and total count for a vector of values in a single fast pass."""
    if not values:
        return ZoneMap(min_value=None, max_value=None, null_count=0, count=0)

    non_null_count = 0
    min_v = None
    max_v = None

    for v in values:
        if v is not None:
            non_null_count += 1
            if min_v is None:
                min_v = v
                max_v = v
            else:
                try:
                    if v < min_v:
                        min_v = v
                    elif v > max_v:
                        max_v = v
                except TypeError:
                    pass

    return ZoneMap(
        min_value=min_v,
        max_value=max_v,
        null_count=len(values) - non_null_count,
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
        n_vals = len(values)

        if n_vals == 0:
            raw_bytes = encode_raw(values, dtype)
            return raw_bytes, EncodingType.RAW, zone_map, 0

        best_bytes = None
        best_enc = None

        if dtype == DataType.BOOL:
            packed_bytes = encode_bitpacked_bool(values)
            best_bytes = packed_bytes
            best_enc = EncodingType.BIT_PACKED_BOOL

        elif dtype in (DataType.INT32, DataType.INT64, DataType.TIMESTAMP):
            # Check Delta / FoR
            try:
                delta_bytes = encode_delta(values, dtype)
                best_bytes = delta_bytes
                best_enc = EncodingType.DELTA
            except Exception:
                pass

            # Check RLE only if data shows repeated runs in initial sample
            try:
                has_runs = (n_vals < 32) or any(values[i] == values[i+1] for i in range(min(31, n_vals - 1)))
                if has_runs:
                    rle_bytes = encode_rle(values, dtype)
                    if rle_bytes and (best_bytes is None or len(rle_bytes) < len(best_bytes)):
                        best_bytes = rle_bytes
                        best_enc = EncodingType.RLE
            except Exception:
                pass

        elif dtype == DataType.STRING:
            # Check Dictionary encoding: sample with stride up to 512 items
            try:
                sample_sz = min(512, n_vals)
                sample = values[::max(1, n_vals // sample_sz)]
                if len(set(sample)) < len(sample) * 0.85:
                    unique_ratio = len(set(values)) / n_vals
                    if unique_ratio < 0.7:
                        dict_bytes = encode_dict(values, dtype)
                        best_bytes = dict_bytes
                        best_enc = EncodingType.DICTIONARY
            except Exception:
                pass

            # Check RLE (encode_rle returns b"" immediately if runs > 60%)
            if best_bytes is None:
                try:
                    rle_bytes = encode_rle(values, dtype)
                    if rle_bytes:
                        best_bytes = rle_bytes
                        best_enc = EncodingType.RLE
                except Exception:
                    pass

        # Fallback to RAW only if no compact encoding was selected
        if best_bytes is None:
            raw_bytes = encode_raw(values, dtype)
            best_bytes = raw_bytes
            best_enc = EncodingType.RAW
            uncompressed_size = len(raw_bytes)
        else:
            if dtype in (DataType.INT64, DataType.INT32, DataType.TIMESTAMP):
                uncompressed_size = 4 + 8 * n_vals
            elif dtype == DataType.BOOL:
                uncompressed_size = 4 + n_vals
            else:
                uncompressed_size = len(best_bytes) * 2

        # Optional lightweight secondary compression with zlib (level 1 for maximum throughput)
        if apply_zlib and len(best_bytes) > 64:
            z_compressed = zlib.compress(best_bytes, level=1)
            if len(z_compressed) + 1 < len(best_bytes):
                final_bytes = b"\x01" + z_compressed
            else:
                final_bytes = b"\x00" + best_bytes
        else:
            final_bytes = b"\x00" + best_bytes

        return final_bytes, best_enc, zone_map, uncompressed_size

    @classmethod
    def decompress(cls, data: Union[bytes, memoryview], enc_type: EncodingType, dtype: DataType) -> List[Any]:
        if not data:
            return []

        # Check if secondary zlib compression was applied
        is_zlib = (data[0] == 1)
        payload = data[1:]

        try:
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
        finally:
            if hasattr(payload, "release"):
                try:
                    payload.release()
                except Exception:
                    pass
            if hasattr(data, "release"):
                try:
                    data.release()
                except Exception:
                    pass

    @classmethod
    def decompress_indices(
        cls,
        data: Union[bytes, memoryview],
        enc_type: EncodingType,
        dtype: DataType,
        indices: List[int]
    ) -> List[Any]:
        if not data or not indices:
            return []

        is_zlib = (data[0] == 1)
        payload = data[1:]

        try:
            if is_zlib:
                payload = zlib.decompress(payload)

            if enc_type == EncodingType.DICTIONARY:
                return decode_dict_indices(payload, dtype, indices)
            elif enc_type == EncodingType.RAW:
                full = decode_raw(payload, dtype)
                return [full[i] for i in indices]
            elif enc_type == EncodingType.BIT_PACKED_BOOL:
                full = decode_bitpacked_bool(payload)
                return [full[i] for i in indices]
            elif enc_type == EncodingType.DELTA:
                full = decode_delta(payload, dtype)
                return [full[i] for i in indices]
            elif enc_type == EncodingType.RLE:
                full = decode_rle(payload, dtype)
                return [full[i] for i in indices]
            else:
                raise ValueError(f"Unknown encoding type: {enc_type}")
        finally:
            if hasattr(payload, "release"):
                try:
                    payload.release()
                except Exception:
                    pass
            if hasattr(data, "release"):
                try:
                    data.release()
                except Exception:
                    pass

    @classmethod
    def evaluate_predicate(
        cls,
        data: Union[bytes, memoryview],
        enc_type: EncodingType,
        dtype: DataType,
        op: str,
        target_val: Any
    ) -> Optional[List[bool]]:
        """
        Attempts to evaluate an equality or inequality filter directly against
        the encoded representation without fully decompressing all elements.
        """
        if not data:
            return None

        # Check if secondary zlib compression was applied
        is_zlib = (data[0] == 1)
        payload = data[1:]

        try:
            if is_zlib:
                payload = zlib.decompress(payload)
            elif isinstance(payload, memoryview):
                payload = bytes(payload)

            if enc_type == EncodingType.DICTIONARY:
                return dict_predicate_pushdown(payload, dtype, op, target_val)
            elif enc_type == EncodingType.RAW:
                return raw_predicate_pushdown(payload, dtype, op, target_val)
            elif enc_type == EncodingType.DELTA:
                return delta_predicate_pushdown(payload, dtype, op, target_val)
            elif enc_type == EncodingType.RLE:
                return rle_predicate_pushdown(payload, dtype, op, target_val)
            elif enc_type == EncodingType.BIT_PACKED_BOOL:
                return bitpacked_bool_predicate_pushdown(payload, dtype, op, target_val)

            return None
        finally:
            if hasattr(payload, "release"):
                try:
                    payload.release()
                except Exception:
                    pass
            if hasattr(data, "release"):
                try:
                    data.release()
                except Exception:
                    pass
