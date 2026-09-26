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

def cast_value(val: Any, dtype: DataType) -> Any:
    """Safely cast a raw Python value to the expected type."""
    if val is None:
        return None
    try:
        if dtype == DataType.INT32 or dtype == DataType.INT64 or dtype == DataType.TIMESTAMP:
            return int(val)
        elif dtype == DataType.FLOAT32 or dtype == DataType.FLOAT64:
            return float(val)
        elif dtype == DataType.BOOL:
            if isinstance(val, str):
                return val.lower() in ("true", "1", "yes", "t")
            return bool(val)
        elif dtype == DataType.STRING:
            return str(val)
        return val
    except Exception as e:
        raise ValueError(f"Cannot cast value {repr(val)} to {dtype.name}: {e}")
