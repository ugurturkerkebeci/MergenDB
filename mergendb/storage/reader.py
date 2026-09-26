import os
import struct
import json
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple, Iterator
from mergendb.core.schema import Schema
from mergendb.core.types import DataType
from mergendb.core.block import BlockMeta, ZoneMap
from mergendb.compression.encodings import EncodingType
from mergendb.compression.compressor import ColumnCompressor
from mergendb.storage.format import MAGIC_HEADER, MAGIC_FOOTER, FORMAT_VERSION, HEADER_FIXED_SIZE

@dataclass
class ScanStats:
    total_blocks: int = 0
    blocks_scanned: int = 0
    blocks_skipped: int = 0
    bytes_read: int = 0
    rows_scanned: int = 0

@dataclass
class ColumnBatch:
    columns: Dict[str, List[Any]]
    row_count: int

class FileReader:
    """
    Reads MergenDB (.mgdb) columnar files with zero-waste column pruning and ZoneMap block skipping.
    """

    def __init__(self, filepath: str):
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")

        self.filepath = filepath
        self._file_size = os.path.getsize(filepath)
        self._file = open(filepath, "rb")

        self.schema: Schema = None
        self.blocks: List[BlockMeta] = []
        self.total_rows: int = 0

        self._read_metadata()

    def _read_metadata(self):
        # 1. Read and verify Header
        self._file.seek(0)
        magic = self._file.read(4)
        if magic != MAGIC_HEADER:
            raise ValueError(f"Invalid file format: magic bytes {magic} do not match {MAGIC_HEADER}")

        version, flags = struct.unpack("<HH", self._file.read(4))
        if version > FORMAT_VERSION:
            raise ValueError(f"Unsupported MergenDB version: {version}")

        created_ts = struct.unpack("<q", self._file.read(8))[0]
        schema_len = struct.unpack("<I", self._file.read(4))[0]
        schema_json = self._file.read(schema_len).decode("utf-8")
        self.schema = Schema.from_json(schema_json)

        # 2. Read Footer from end of file
        # Footer layout: [Footer JSON bytes] + [Footer Len (4B)] + [Magic Footer (4B)]
        self._file.seek(self._file_size - 8)
        footer_len, footer_magic = struct.unpack("<II", self._file.read(8))
        if struct.pack("<I", footer_magic) != MAGIC_FOOTER:
            raise ValueError("Corrupt file: missing or invalid footer magic.")

        self._file.seek(self._file_size - 8 - footer_len)
        footer_json = self._file.read(footer_len).decode("utf-8")
        footer_data = json.loads(footer_json)

        self.total_rows = footer_data.get("total_rows", 0)
        self.blocks = [BlockMeta.from_dict(b) for b in footer_data.get("blocks", [])]

    def _read_columns(self, block: BlockMeta, col_names: List[str], stats: ScanStats) -> Dict[str, List[Any]]:
        result = {}
        for col_name in col_names:
            chunk_meta = block.columns[col_name]
            col_def = self.schema.get_column(col_name)
            self._file.seek(chunk_meta.offset)
            chunk_bytes = self._file.read(chunk_meta.compressed_bytes)
            stats.bytes_read += len(chunk_bytes)
            result[col_name] = ColumnCompressor.decompress(
                chunk_bytes,
                EncodingType(chunk_meta.encoding),
                col_def.data_type
            )
        return result

    def scan(
        self,
        columns: Optional[List[str]] = None,
        predicates: Optional[List[Tuple[str, str, Any]]] = None,
        filter_columns: Optional[List[str]] = None,
        filter_fn: Optional[Any] = None
    ) -> Iterator[Tuple[ColumnBatch, ScanStats]]:
        """
        Scans data blocks with filter pushdown, ZoneMap pruning, and Late Materialization.

        Args:
            columns: Specific column names to load. If None, loads all columns.
            predicates: Pushdown filters in form of (column_name, operator, value), e.g. [("age", ">", 30)]
            filter_columns: Columns required to evaluate WHERE filter.
            filter_fn: Callable evaluating WHERE mask on filter column data.

        Yields:
            (ColumnBatch, ScanStats)
        """
        target_columns = columns if columns is not None else self.schema.column_names()
        for col_name in target_columns:
            if not self.schema.has_column(col_name):
                raise KeyError(f"Column '{col_name}' does not exist in schema.")

        stats = ScanStats(total_blocks=len(self.blocks))

        for block in self.blocks:
            # 1. ZoneMap Check (Block Pruning)
            skip_block = False
            if predicates:
                for col_name, op, val in predicates:
                    if col_name in block.columns:
                        chunk_meta = block.columns[col_name]
                        if chunk_meta.zone_map.can_prune(op, val):
                            skip_block = True
                            break

            if skip_block:
                stats.blocks_skipped += 1
                continue

            stats.blocks_scanned += 1
            stats.rows_scanned += block.row_count

            # 2. Late Materialization
            if filter_columns and filter_fn and set(filter_columns).issubset(block.columns.keys()):
                # Read ONLY the filter columns first
                filter_data = self._read_columns(block, filter_columns, stats)
                mask = filter_fn(filter_data)

                # Count matching rows
                match_count = sum(1 for m in mask if m)
                if match_count == 0:
                    # ZERO rows in this block match the filter!
                    # Skip reading/decompressing the remaining columns completely!
                    continue

                # Rows matched! Read only the remaining requested columns
                remaining_cols = [c for c in target_columns if c not in filter_columns]
                if remaining_cols:
                    rest_data = self._read_columns(block, remaining_cols, stats)
                    filter_data.update(rest_data)

                # Filter column vectors by mask
                batch_data = {
                    c: [v for v, m in zip(filter_data[c], mask) if m]
                    for c in target_columns
                }
                yield ColumnBatch(columns=batch_data, row_count=match_count), stats

            else:
                # Standard columnar read
                batch_data = self._read_columns(block, target_columns, stats)
                yield ColumnBatch(columns=batch_data, row_count=block.row_count), stats

    def close(self):
        if not self._file.closed:
            self._file.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
