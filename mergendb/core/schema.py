from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Any
import json
from mergendb.core.types import DataType

@dataclass
class ColumnDef:
    name: str
    data_type: DataType
    nullable: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "data_type": int(self.data_type),
            "nullable": self.nullable
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ColumnDef":
        return cls(
            name=d["name"],
            data_type=DataType(d["data_type"]),
            nullable=d.get("nullable", False)
        )

class Schema:
    def __init__(self, columns: List[ColumnDef]):
        self.columns = columns
        self._name_to_col: Dict[str, ColumnDef] = {c.name: c for c in columns}
        self._name_to_idx: Dict[str, int] = {c.name: i for i, c in enumerate(columns)}

    def get_column(self, name: str) -> Optional[ColumnDef]:
        return self._name_to_col.get(name)

    def get_column_index(self, name: str) -> int:
        if name not in self._name_to_idx:
            raise KeyError(f"Column '{name}' not found in schema.")
        return self._name_to_idx[name]

    def has_column(self, name: str) -> bool:
        return name in self._name_to_col

    def column_names(self) -> List[str]:
        return [c.name for c in self.columns]

    def to_json(self) -> str:
        return json.dumps([c.to_dict() for c in self.columns])

    @classmethod
    def from_json(cls, json_str: str) -> "Schema":
        data = json.loads(json_str)
        return cls([ColumnDef.from_dict(d) for d in data])

    def __repr__(self) -> str:
        cols_str = ", ".join(f"{c.name}: {c.data_type.name}" for c in self.columns)
        return f"Schema({cols_str})"
