import zlib
from typing import Any, Optional, Iterable

class BlockBloomFilter:
    """
    Lightweight, deterministic, 256-bit block-level Bloom Filter.
    Zero external dependencies, pure Python bitwise operations with C-accelerated zlib.crc32.
    Guarantees 0% false negatives for equality predicates (col == 'target' or col = 'target').
    """
    BITS = 1024
    NUM_HASHES = 4

    def __init__(self, bitmask: int = 0):
        self.bitmask = bitmask

    @classmethod
    def _hashes(cls, val: Any) -> Iterable[int]:
        if val is None:
            return ()
        s = str(val).encode("utf-8")
        h1 = zlib.crc32(s)
        h2 = ((h1 >> 16) ^ (h1 * 0x45d9f3b)) & 0xFFFFFFFF
        for i in range(cls.NUM_HASHES):
            yield ((h1 + i * h2) & 0xFFFFFFFF) % cls.BITS

    def add(self, val: Any):
        if val is not None:
            for bit_pos in self._hashes(val):
                self.bitmask |= (1 << bit_pos)

    def contains(self, val: Any) -> bool:
        """
        Returns False if the value is DEFINITELY NOT present in this block.
        Returns True if the value MIGHT be present.
        """
        if val is None:
            return True
        for bit_pos in self._hashes(val):
            if not (self.bitmask & (1 << bit_pos)):
                return False
        return True

    @classmethod
    def build_from_values(cls, values: Iterable[Any]) -> "BlockBloomFilter":
        bitmask = 0
        bits = cls.BITS
        crc = zlib.crc32
        for v in values:
            if v is not None:
                s = str(v).encode("utf-8")
                h1 = crc(s)
                h2 = ((h1 >> 16) ^ (h1 * 0x45d9f3b)) & 0xFFFFFFFF
                bitmask |= (1 << (h1 % bits)) | (1 << ((h1 + h2) % bits)) | (1 << ((h1 + (h2 << 1)) % bits)) | (1 << ((h1 + 3 * h2) % bits))
        return cls(bitmask)

    def to_hex(self) -> str:
        return hex(self.bitmask)

    @classmethod
    def from_hex(cls, h: Optional[str]) -> Optional["BlockBloomFilter"]:
        if not h:
            return None
        try:
            return cls(int(h, 16))
        except (ValueError, TypeError):
            return None
