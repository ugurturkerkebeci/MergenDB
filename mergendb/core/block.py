from dataclasses import dataclass
from typing import Any, Optional, Dict
import json
from mergendb.core.types import DataType

@dataclass
class ZoneMap:
    min_value: Any
    max_value: Any
    null_count: int = 0
    count: int = 0

    def can_prune(self, op: str, value: Any) -> bool:
        """
        Determines if the entire block can be skipped without reading or decompressing.
        Returns True if NO row in this block can possibly satisfy the condition (column OP value).
        """
        if self.count == 0 or self.min_value is None or self.max_value is None:
            return False

        # Type coercion for safe and accurate comparisons
        comp_val = value
        if isinstance(self.min_value, str) and not isinstance(value, str):
            comp_val = str(value)
        elif isinstance(self.min_value, (int, float)) and isinstance(value, str):
            try:
                comp_val = int(value) if isinstance(self.min_value, int) else float(value)
            except (ValueError, TypeError):
                pass

        try:
            if op == "==" or op == "=":
                return comp_val < self.min_value or comp_val > self.max_value
            elif op == "!=":
                return self.min_value == self.max_value == comp_val
            elif op == ">":
                return self.max_value <= comp_val
            elif op == ">=":
                return self.max_value < comp_val
            elif op == "<":
                return self.min_value >= comp_val
            elif op == "<=":
                return self.min_value > comp_val
        except TypeError:
            # Incomparable types, safe fallback is not to prune
            return False

        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "min": self.min_value,
            "max": self.max_value,
            "nulls": self.null_count,
            "count": self.count
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ZoneMap":
        return cls(
            min_value=d.get("min"),
            max_value=d.get("max"),
            null_count=d.get("nulls", 0),
            count=d.get("count", 0)
        )

@dataclass
class ColumnChunkMeta:
    column_name: str
    encoding: int
    offset: int
    compressed_bytes: int
    uncompressed_bytes: int
    row_count: int
    zone_map: ZoneMap

    def to_dict(self) -> Dict[str, Any]:
        return {
            "col": self.column_name,
            "enc": self.encoding,
            "offset": self.offset,
            "c_bytes": self.compressed_bytes,
            "u_bytes": self.uncompressed_bytes,
            "rows": self.row_count,
            "zm": self.zone_map.to_dict()
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ColumnChunkMeta":
        return cls(
            column_name=d["col"],
            encoding=d["enc"],
            offset=d["offset"],
            compressed_bytes=d["c_bytes"],
            uncompressed_bytes=d["u_bytes"],
            row_count=d["rows"],
            zone_map=ZoneMap.from_dict(d["zm"])
        )

@dataclass
class BlockMeta:
    block_id: int
    row_count: int
    columns: Dict[str, ColumnChunkMeta]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.block_id,
            "rows": self.row_count,
            "cols": {name: chunk.to_dict() for name, chunk in self.columns.items()}
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "BlockMeta":
        return cls(
            block_id=d["id"],
            row_count=d["rows"],
            columns={name: ColumnChunkMeta.from_dict(c) for name, c in d["cols"].items()}
        )
