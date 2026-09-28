from enum import IntEnum
import struct
from typing import Any, Tuple, Optional

class DataType(IntEnum):
    INT32 = 1
    INT64 = 2
    FLOAT32 = 3
    FLOAT64 = 4
    BOOL = 5
    STRING = 6
    TIMESTAMP = 7

# Byte representations and format codes for fixed-width types
TYPE_STRUCT_FORMAT = {
    DataType.INT32: "<i",      # 4-byte signed int
    DataType.INT64: "<q",      # 8-byte signed int
    DataType.FLOAT32: "<f",    # 4-byte single precision
    DataType.FLOAT64: "<d",    # 8-byte double precision
    DataType.BOOL: "<?",       # 1-byte bool
    DataType.TIMESTAMP: "<q",  # 8-byte timestamp (unix microseconds)
}

TYPE_FIXED_SIZES = {
    DataType.INT32: 4,
    DataType.INT64: 8,
    DataType.FLOAT32: 4,
    DataType.FLOAT64: 8,
    DataType.BOOL: 1,
    DataType.TIMESTAMP: 8,
}

def is_numeric(dtype: DataType) -> bool:
    return dtype in (DataType.INT32, DataType.INT64, DataType.FLOAT32, DataType.FLOAT64, DataType.TIMESTAMP)

def cast_value(val: Any, dtype: DataType, safe: bool = True) -> Any:
    """Safely cast a raw Python value to the expected type with zero crash tolerance."""
    if val is None:
        return None
    try:
        # Check dirty null tokens
        if isinstance(val, str):
            v_strip = val.strip()
            v_upper = v_strip.upper()
            if dtype != DataType.STRING:
                if v_upper in ("", "NULL", "NONE", "N/A", "NA", "NAN", "\\N", "NIL", "-"):
                    return None
            else:
                if v_upper in ("NULL", "\\N"):
                    return None

        if dtype in (DataType.INT32, DataType.INT64, DataType.TIMESTAMP):
            if isinstance(val, (int, float)):
                return int(val)
            v_str = str(val).strip()
            try:
                return int(v_str)
            except ValueError:
                # Handle floats represented as strings like "42.0"
                try:
                    return int(float(v_str))
                except (ValueError, OverflowError):
                    if safe:
                        return None
                    raise

        elif dtype in (DataType.FLOAT32, DataType.FLOAT64):
            if isinstance(val, (int, float)):
                return float(val)
            v_str = str(val).strip()
            try:
                return float(v_str)
            except (ValueError, OverflowError):
                if safe:
                    return None
                raise

        elif dtype == DataType.BOOL:
            if isinstance(val, str):
                v_clean = val.strip().lower()
                if v_clean in ("true", "1", "yes", "t", "y", "on"):
                    return True
                if v_clean in ("false", "0", "no", "f", "n", "off"):
                    return False
                return False if safe else (len(v_clean) > 0)
            return bool(val)

        elif dtype == DataType.STRING:
            if isinstance(val, (bytes, bytearray, memoryview)):
                try:
                    return bytes(val).decode("utf-8", errors="replace")
                except Exception:
                    return str(val)
            return str(val)

        return val
    except Exception as e:
        if safe:
            return None
        raise ValueError(f"Cannot cast value {repr(val)} to {dtype.name}: {e}")

