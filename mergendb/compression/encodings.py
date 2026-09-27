import struct
import array
from enum import IntEnum
from typing import List, Any, Tuple, Optional, Union
from mergendb.core.types import DataType, TYPE_STRUCT_FORMAT, TYPE_FIXED_SIZES

class EncodingType(IntEnum):
    RAW = 0
    RLE = 1
    DICTIONARY = 2
    DELTA = 3
    BIT_PACKED_BOOL = 4

ARRAY_TYPECODES = {
    DataType.INT32: "i",
    DataType.INT64: "q",
    DataType.FLOAT32: "f",
    DataType.FLOAT64: "d",
    DataType.TIMESTAMP: "q",
}

# -------------------------------------------------------------
# Raw Encoding / Decoding
# -------------------------------------------------------------
def encode_raw(values: List[Any], dtype: DataType) -> bytes:
    count = len(values)
    buf = bytearray()
    # Header: item count
    buf.extend(struct.pack("<I", count))

    if dtype == DataType.STRING:
        for v in values:
            if v is None:
                buf.extend(struct.pack("<i", -1))
            else:
                encoded = str(v).encode("utf-8")
                buf.extend(struct.pack("<i", len(encoded)))
                buf.extend(encoded)
    elif dtype in ARRAY_TYPECODES:
        tc = ARRAY_TYPECODES[dtype]
        clean_vals = [0 if v is None else v for v in values]
        buf.extend(array.array(tc, clean_vals).tobytes())
    else:
        fmt = TYPE_STRUCT_FORMAT[dtype]
        default_val = 0 if dtype != DataType.BOOL else False
        for v in values:
            val = default_val if v is None else v
            buf.extend(struct.pack(fmt, val))

    return bytes(buf)

def decode_raw(data: bytes, dtype: DataType) -> List[Any]:
    if len(data) < 4:
        return []
    count = struct.unpack_from("<I", data, 0)[0]
    offset = 4
    values = []

    if dtype == DataType.STRING:
        for _ in range(count):
            length = struct.unpack_from("<i", data, offset)[0]
            offset += 4
            if length == -1:
                values.append(None)
            else:
                s = bytes(data[offset : offset + length]).decode("utf-8")
                offset += length
                values.append(s)
    elif dtype in ARRAY_TYPECODES:
        tc = ARRAY_TYPECODES[dtype]
        size = TYPE_FIXED_SIZES[dtype]
        arr = array.array(tc)
        arr.frombytes(data[offset : offset + count * size])
        return arr.tolist()
    else:
        fmt = TYPE_STRUCT_FORMAT[dtype]
        size = struct.calcsize(fmt)
        for _ in range(count):
            val = struct.unpack_from(fmt, data, offset)[0]
            offset += size
            values.append(val)
    return values

# -------------------------------------------------------------
# RLE (Run-Length Encoding)
# -------------------------------------------------------------
def encode_rle(values: List[Any], dtype: DataType) -> bytes:
    if not values:
        return struct.pack("<I", 0)

    runs: List[Tuple[int, Any]] = []
    current_val = values[0]
    current_count = 1

    for val in values[1:]:
        if val == current_val:
            current_count += 1
        else:
            runs.append((current_count, current_val))
            current_val = val
            current_count = 1
    runs.append((current_count, current_val))

    # Early abort if runs ratio is too high (cannot compress effectively)
    if len(runs) > len(values) * 0.6:
        return b""

    buf = bytearray()
    buf.extend(struct.pack("<II", len(values), len(runs)))

    if dtype == DataType.STRING:
        for count, val in runs:
            buf.extend(struct.pack("<I", count))
            if val is None:
                buf.extend(struct.pack("<i", -1))
            else:
                encoded = str(val).encode("utf-8")
                buf.extend(struct.pack("<i", len(encoded)))
                buf.extend(encoded)
    else:
        fmt = TYPE_STRUCT_FORMAT[dtype]
        default_val = 0 if dtype != DataType.BOOL else False
        for count, val in runs:
            buf.extend(struct.pack("<I", count))
            v = default_val if val is None else val
            buf.extend(struct.pack(fmt, v))

    return bytes(buf)

def decode_rle(data: bytes, dtype: DataType) -> List[Any]:
    if len(data) < 8:
        return []
    total_items, num_runs = struct.unpack_from("<II", data, 0)
    offset = 8
    result = []

    if dtype == DataType.STRING:
        for _ in range(num_runs):
            count = struct.unpack_from("<I", data, offset)[0]
            offset += 4
            str_len = struct.unpack_from("<i", data, offset)[0]
            offset += 4
            if str_len == -1:
                val = None
            else:
                val = bytes(data[offset : offset + str_len]).decode("utf-8")
                offset += str_len
            result.extend([val] * count)
    else:
        fmt = TYPE_STRUCT_FORMAT[dtype]
        val_size = struct.calcsize(fmt)
        for _ in range(num_runs):
            count = struct.unpack_from("<I", data, offset)[0]
            offset += 4
            val = struct.unpack_from(fmt, data, offset)[0]
            offset += val_size
            result.extend([val] * count)

    return result

# -------------------------------------------------------------
# Dictionary Encoding
# -------------------------------------------------------------
def encode_dict(values: List[Any], dtype: DataType) -> bytes:
    # Build dictionary
    unique_vals = []
    val_to_idx = {}
    for v in values:
        if v not in val_to_idx:
            val_to_idx[v] = len(unique_vals)
            unique_vals.append(v)

    dict_size = len(unique_vals)
    buf = bytearray()
    # Header: total items, dict size
    buf.extend(struct.pack("<II", len(values), dict_size))

    # Serialize dictionary entries
    if dtype == DataType.STRING:
        for v in unique_vals:
            if v is None:
                buf.extend(struct.pack("<i", -1))
            else:
                enc = str(v).encode("utf-8")
                buf.extend(struct.pack("<i", len(enc)))
                buf.extend(enc)
    else:
        fmt = TYPE_STRUCT_FORMAT[dtype]
        default_val = 0 if dtype != DataType.BOOL else False
        for v in unique_vals:
            val = default_val if v is None else v
            buf.extend(struct.pack(fmt, val))

    # Serialize codes
    # Use 1 byte if dict <= 256, 2 bytes if <= 65536, else 4 bytes
    if dict_size <= 256:
        buf.extend(struct.pack("<B", 1)) # code byte size
        buf.extend(bytes(val_to_idx[v] for v in values))
    elif dict_size <= 65536:
        buf.extend(struct.pack("<B", 2))
        buf.extend(array.array("H", (val_to_idx[v] for v in values)).tobytes())
    else:
        buf.extend(struct.pack("<B", 4))
        buf.extend(array.array("I", (val_to_idx[v] for v in values)).tobytes())

    return bytes(buf)

def decode_dict(data: bytes, dtype: DataType) -> List[Any]:
    if len(data) < 8:
        return []
    total_items, dict_size = struct.unpack_from("<II", data, 0)
    offset = 8

    # Read dictionary
    unique_vals = []
    if dtype == DataType.STRING:
        for _ in range(dict_size):
            str_len = struct.unpack_from("<i", data, offset)[0]
            offset += 4
            if str_len == -1:
                unique_vals.append(None)
            else:
                val = bytes(data[offset : offset + str_len]).decode("utf-8")
                offset += str_len
                unique_vals.append(val)
    else:
        fmt = TYPE_STRUCT_FORMAT[dtype]
        val_size = struct.calcsize(fmt)
        for _ in range(dict_size):
            val = struct.unpack_from(fmt, data, offset)[0]
            offset += val_size
            unique_vals.append(val)

    # Read codes
    code_size = struct.unpack_from("<B", data, offset)[0]
    offset += 1

    if code_size == 1:
        raw_codes = data[offset : offset + total_items]
        return [unique_vals[c] for c in raw_codes]
    elif code_size == 2:
        codes = array.array("H")
        codes.frombytes(data[offset : offset + total_items * 2])
        return [unique_vals[c] for c in codes]
    else:
        codes = array.array("I")
        codes.frombytes(data[offset : offset + total_items * 4])
        return [unique_vals[c] for c in codes]

def dict_predicate_pushdown(
    data: Union[bytes, memoryview],
    dtype: DataType,
    op: str,
    target_val: Any
) -> Optional[List[bool]]:
    """
    Evaluates binary equality/inequality predicates directly against dictionary codes
    without expanding all unique string/value objects for every row in the block.
    Returns None if pushdown cannot evaluate this operator.
    """
    if op not in ("==", "=", "!=", "<>"):
        return None

    if not data or len(data) < 8:
        return None

    total_items, dict_size = struct.unpack_from("<II", data, 0)
    offset = 8

    unique_vals = []
    if dtype == DataType.STRING:
        target_str = str(target_val) if target_val is not None else None
        for _ in range(dict_size):
            str_len = struct.unpack_from("<i", data, offset)[0]
            offset += 4
            if str_len == -1:
                unique_vals.append(None)
            else:
                unique_vals.append(bytes(data[offset : offset + str_len]).decode("utf-8"))
                offset += str_len
        target = target_str
    else:
        fmt = TYPE_STRUCT_FORMAT[dtype]
        val_size = struct.calcsize(fmt)
        for _ in range(dict_size):
            val = struct.unpack_from(fmt, data, offset)[0]
            offset += val_size
            unique_vals.append(val)
        target = target_val

    is_eq = op in ("==", "=")

    if target not in unique_vals:
        return [False] * total_items if is_eq else [True] * total_items

    target_code = unique_vals.index(target)
    code_size = struct.unpack_from("<B", data, offset)[0]
    offset += 1

    if code_size == 1:
        raw_codes = data[offset : offset + total_items]
        if is_eq:
            return [c == target_code for c in raw_codes]
        else:
            return [c != target_code for c in raw_codes]
    elif code_size == 2:
        codes = array.array("H")
        codes.frombytes(data[offset : offset + total_items * 2])
        if is_eq:
            return [c == target_code for c in codes]
        else:
            return [c != target_code for c in codes]
    else:
        codes = array.array("I")
        codes.frombytes(data[offset : offset + total_items * 4])
        if is_eq:
            return [c == target_code for c in codes]
        else:
            return [c != target_code for c in codes]

# -------------------------------------------------------------
# Delta / Frame-of-Reference (FoR) for Integers
# -------------------------------------------------------------
def encode_delta(values: List[Any], dtype: DataType) -> bytes:
    if not values:
        return struct.pack("<I", 0)

    clean_vals = [0 if v is None else int(v) for v in values]
    min_val = min(clean_vals)
    deltas = [v - min_val for v in clean_vals]
    max_delta = max(deltas)

    buf = bytearray()
    # Header: count, base (min_val: 8-byte int64)
    buf.extend(struct.pack("<Iq", len(values), min_val))

    if max_delta < 256:
        buf.extend(struct.pack("<B", 1))  # 1 byte per delta
        buf.extend(bytes(deltas))
    elif max_delta < 65536:
        buf.extend(struct.pack("<B", 2))  # 2 bytes per delta
        buf.extend(array.array("H", deltas).tobytes())
    elif max_delta < 4294967296:
        buf.extend(struct.pack("<B", 4))  # 4 bytes per delta
        buf.extend(array.array("I", deltas).tobytes())
    else:
        buf.extend(struct.pack("<B", 8))  # 8 bytes per delta
        buf.extend(array.array("Q", deltas).tobytes())

    return bytes(buf)

def decode_delta(data: bytes, dtype: DataType) -> List[Any]:
    if len(data) < 12:
        return []
    count, min_val = struct.unpack_from("<Iq", data, 0)
    byte_width = struct.unpack_from("<B", data, 12)[0]
    offset = 13

    if byte_width == 1:
        deltas = data[offset : offset + count]
    elif byte_width == 2:
        arr = array.array("H")
        arr.frombytes(data[offset : offset + count * 2])
        deltas = arr
    elif byte_width == 4:
        arr = array.array("I")
        arr.frombytes(data[offset : offset + count * 4])
        deltas = arr
    else:
        arr = array.array("Q")
        arr.frombytes(data[offset : offset + count * 8])
        deltas = arr

    return [min_val + d for d in deltas]

# -------------------------------------------------------------
# Bit-Packed Booleans (8 booleans in 1 byte!)
# -------------------------------------------------------------
def encode_bitpacked_bool(values: List[Any]) -> bytes:
    count = len(values)
    buf = bytearray()
    buf.extend(struct.pack("<I", count))

    current_byte = 0
    bit_pos = 0

    for v in values:
        if bool(v):
            current_byte |= (1 << bit_pos)
        bit_pos += 1
        if bit_pos == 8:
            buf.append(current_byte)
            current_byte = 0
            bit_pos = 0

    if bit_pos > 0:
        buf.append(current_byte)

    return bytes(buf)

def decode_bitpacked_bool(data: bytes) -> List[bool]:
    if len(data) < 4:
        return []
    count = struct.unpack_from("<I", data, 0)[0]
    offset = 4
    result = []

    for i in range(count):
        byte_idx = offset + (i // 8)
        bit_idx = i % 8
        b = data[byte_idx]
        val = bool((b >> bit_idx) & 1)
        result.append(val)

    return result
