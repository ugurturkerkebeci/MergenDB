"""
MergenDB Vector Math & Similarity Module (Zero external dependencies).
Provides ultra-fast vector distance and similarity calculations using native Python buffers/structs.
"""

import math
import struct
from typing import List, Union, Sequence, Optional, Any

VectorType = Union[List[float], Sequence[float], bytes, memoryview]

def parse_vector(v: Any) -> List[float]:
    """Converts a vector representation (list, tuple, json string, comma-separated str) to a list of floats."""
    if v is None:
        return []
    if isinstance(v, (list, tuple)):
        return [float(x) for x in v]
    if isinstance(v, (bytes, bytearray, memoryview)):
        # Contiguous IEEE-754 32-bit floats
        b = bytes(v)
        n = len(b) // 4
        return list(struct.unpack(f"<{n}f", b[:n*4]))
    if isinstance(v, str):
        v = v.strip()
        if v.startswith("[") and v.endswith("]"):
            v = v[1:-1]
        if not v:
            return []
        parts = [p.strip() for p in v.split(",") if p.strip()]
        return [float(p) for p in parts]
    raise TypeError(f"Cannot parse vector from type {type(v).__name__}")

def vector_to_bytes(v: Sequence[float]) -> bytes:
    """Serializes a float sequence into contiguous float32 little-endian bytes."""
    return struct.pack(f"<{len(v)}f", *[float(x) for x in v])

def bytes_to_vector(b: Union[bytes, bytearray, memoryview]) -> List[float]:
    """Deserializes contiguous float32 little-endian bytes into a float list."""
    b_val = bytes(b)
    n = len(b_val) // 4
    if n == 0:
        return []
    return list(struct.unpack(f"<{n}f", b_val[:n * 4]))

def dot_product(v1: Sequence[float], v2: Sequence[float]) -> float:
    """Computes the dot product of two vectors."""
    n = min(len(v1), len(v2))
    total = 0.0
    for i in range(n):
        total += v1[i] * v2[i]
    return total

def l2_norm(v: Sequence[float]) -> float:
    """Computes the Euclidean norm (magnitude) of a vector."""
    total = 0.0
    for x in v:
        total += x * x
    return math.sqrt(total)

def cosine_similarity(v1: Sequence[float], v2: Sequence[float]) -> float:
    """Computes cosine similarity in range [-1.0, 1.0]."""
    n = min(len(v1), len(v2))
    if n == 0:
        return 0.0
    dot = 0.0
    norm1 = 0.0
    norm2 = 0.0
    for i in range(n):
        x = v1[i]
        y = v2[i]
        dot += x * y
        norm1 += x * x
        norm2 += y * y
    if norm1 <= 0.0 or norm2 <= 0.0:
        return 0.0
    denom = math.sqrt(norm1) * math.sqrt(norm2)
    val = dot / denom
    if val > 1.0:
        return 1.0
    if val < -1.0:
        return -1.0
    return val

def cosine_distance(v1: Sequence[float], v2: Sequence[float]) -> float:
    """Computes cosine distance: 1.0 - cosine_similarity."""
    return 1.0 - cosine_similarity(v1, v2)

def l2_distance(v1: Sequence[float], v2: Sequence[float]) -> float:
    """Computes Euclidean (L2) distance."""
    n = min(len(v1), len(v2))
    total = 0.0
    for i in range(n):
        diff = v1[i] - v2[i]
        total += diff * diff
    return math.sqrt(total)

def manhattan_distance(v1: Sequence[float], v2: Sequence[float]) -> float:
    """Computes Manhattan (L1) distance."""
    n = min(len(v1), len(v2))
    total = 0.0
    for i in range(n):
        total += abs(v1[i] - v2[i])
    return total
