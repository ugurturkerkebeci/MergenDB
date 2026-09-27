import os
import struct
import json
import mmap
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple, Iterator, Union, Set
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


class LazyColumnDict(dict):
    """
    On-demand columnar decompressor.
    Only reads and decompresses a column when that column is explicitly accessed
    by an expression evaluator. Enables instant short-circuiting of multi-column conditions.
    """
    def __init__(self, reader: "FileReader", block: BlockMeta, stats: ScanStats):
        super().__init__()
        self.reader = reader
        self.block = block
        self.stats = stats
        self.row_count = block.row_count

    def __getitem__(self, key: str) -> List[Any]:
        if not super().__contains__(key):
            if key not in self.block.columns:
                raise KeyError(f"Column '{key}' not in block columns.")
            chunk_meta = self.block.columns[key]
            col_def = self.reader.schema.get_column(key)
            chunk_bytes = self.reader.read_chunk_bytes(chunk_meta.offset, chunk_meta.compressed_bytes)
            self.stats.bytes_read += len(chunk_bytes)
            val = ColumnCompressor.decompress(
                chunk_bytes,
                EncodingType(chunk_meta.encoding),
                col_def.data_type
            )
            super().__setitem__(key, val)
            return val
        return super().__getitem__(key)

    def evaluate_predicate(self, col_name: str, op: str, target_val: Any) -> Optional[List[bool]]:
        """
        Attempts fast predicate evaluation directly on encoded/dictionary data
        without expanding and decoding all rows to Python objects.
        Returns None if fast pushdown is not supported for this column/encoding.
        """
        if col_name not in self.block.columns:
            return None
        # If already decompressed in memory, let expression evaluator use standard in-memory path
        if super().__contains__(col_name):
            return None
        chunk_meta = self.block.columns[col_name]
        col_def = self.reader.schema.get_column(col_name)
        chunk_bytes = self.reader.read_chunk_bytes(chunk_meta.offset, chunk_meta.compressed_bytes)
        self.stats.bytes_read += len(chunk_bytes)
        return ColumnCompressor.evaluate_predicate(
            chunk_bytes,
            EncodingType(chunk_meta.encoding),
            col_def.data_type,
            op,
            target_val
        )

    def __contains__(self, key: object) -> bool:
        return super().__contains__(key) or (isinstance(key, str) and key in self.block.columns)

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default


class FileReader:
    """
    Reads MergenDB (.mgdb) columnar files with zero-copy mmap I/O, column pruning, and ZoneMap skipping.
    """

    def __init__(self, filepath: str):
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")

        self.filepath = filepath
        self._file_size = os.path.getsize(filepath)
        self._file = open(filepath, "rb")
        self._mmap: Optional[mmap.mmap] = None
        if self._file_size > 0:
            try:
                self._mmap = mmap.mmap(self._file.fileno(), 0, access=mmap.ACCESS_READ)
            except Exception:
                self._mmap = None

        self.schema: Schema = None
        self.blocks: List[BlockMeta] = []
        self.total_rows: int = 0

        self._read_metadata()

    def read_chunk_bytes(self, offset: int, length: int) -> Union[bytes, memoryview]:
        """
        Reads chunk bytes with zero-copy mmap if available, or falls back to seek/read.
        """
        if self._mmap is not None:
            return memoryview(self._mmap)[offset : offset + length]
        self._file.seek(offset)
        return self._file.read(length)

    def _read_metadata(self):
        # 1. Read Header
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
            chunk_bytes = self.read_chunk_bytes(chunk_meta.offset, chunk_meta.compressed_bytes)
            stats.bytes_read += len(chunk_bytes)
            result[col_name] = ColumnCompressor.decompress(
                chunk_bytes,
                EncodingType(chunk_meta.encoding),
                col_def.data_type
            )
        return result

    def _scan_single_block(
        self,
        block: BlockMeta,
        target_columns: List[str],
        predicates: Optional[List[Tuple[str, str, Any]]],
        filter_cols_set: Set[str],
        filter_fn: Optional[Any]
    ) -> Tuple[Optional[ColumnBatch], int, bool]:
        """
        Scans a single block.
        Returns: (batch, bytes_read, was_skipped)
        """
        # 1. ZoneMap check (Block Pruning)
        if predicates:
            for col_name, op, val in predicates:
                if col_name in block.columns:
                    chunk_meta = block.columns[col_name]
                    if chunk_meta.zone_map.can_prune(op, val):
                        return None, 0, True

        # 2. Late Materialization via Demand-Driven Lazy Column Loading
        if filter_cols_set and filter_fn and filter_cols_set.issubset(block.columns.keys()):
            from itertools import compress
            block_stats = ScanStats()
            lazy_data = LazyColumnDict(self, block, block_stats)
            mask = filter_fn(lazy_data)
            bytes_read = block_stats.bytes_read

            # Fast short-circuit: if no rows match, skip immediately
            if not any(mask):
                return None, bytes_read, False

            match_count = mask.count(True) if hasattr(mask, "count") else sum(1 for m in mask if m)

            # Optimization: If all rows matched, avoid filtering overhead
            if match_count == block.row_count:
                batch_data = {c: lazy_data[c] for c in target_columns}
            else:
                # High-speed C-level filtering using itertools.compress
                batch_data = {
                    c: list(compress(lazy_data[c], mask))
                    for c in target_columns
                }
            return ColumnBatch(columns=batch_data, row_count=match_count), block_stats.bytes_read, False

        else:
            # Standard columnar read
            block_stats = ScanStats()
            batch_data = self._read_columns(block, target_columns, block_stats)
            return ColumnBatch(columns=batch_data, row_count=block.row_count), block_stats.bytes_read, False

    def scan(
        self,
        columns: Optional[List[str]] = None,
        predicates: Optional[List[Tuple[str, str, Any]]] = None,
        filter_columns: Optional[List[str]] = None,
        filter_fn: Optional[Any] = None,
        parallel: bool = True,
        max_workers: Optional[int] = None
    ) -> Iterator[Tuple[ColumnBatch, ScanStats]]:
        """
        Scans data blocks with filter pushdown, ZoneMap pruning, Late Materialization,
        and automatic multi-core parallel block processing.

        Args:
            columns: Specific column names to load. If None, loads all columns.
            predicates: Pushdown filters in form of (column_name, operator, value), e.g. [("age", ">", 30)]
            filter_columns: Columns required to evaluate WHERE filter.
            filter_fn: Callable evaluating WHERE mask on filter column data.
            parallel: Whether to enable multi-threaded parallel block scanning when multiple blocks exist.
            max_workers: Maximum worker threads for parallel scan (defaults to CPU core count, max 8).

        Yields:
            (ColumnBatch, ScanStats)
        """
        target_columns = columns if columns is not None else self.schema.column_names()
        for col_name in target_columns:
            if not self.schema.has_column(col_name):
                raise KeyError(f"Column '{col_name}' does not exist in schema.")

        stats = ScanStats(total_blocks=len(self.blocks))
        self.last_scan_stats = stats
        filter_cols_set = set(filter_columns) if filter_columns else set()

        use_parallel = parallel and len(self.blocks) > 2 and self._mmap is not None

        if use_parallel:
            from concurrent.futures import ThreadPoolExecutor
            worker_count = max_workers or min(os.cpu_count() or 4, 8)

            def worker_fn(blk):
                return self._scan_single_block(blk, target_columns, predicates, filter_cols_set, filter_fn)

            with ThreadPoolExecutor(max_workers=worker_count) as executor:
                for block, (batch, b_read, was_skipped) in zip(self.blocks, executor.map(worker_fn, self.blocks)):
                    if was_skipped:
                        stats.blocks_skipped += 1
                        continue
                    stats.blocks_scanned += 1
                    stats.bytes_read += b_read
                    stats.rows_scanned += block.row_count
                    if batch is not None and batch.row_count > 0:
                        yield batch, stats

        else:
            for block in self.blocks:
                batch, b_read, was_skipped = self._scan_single_block(
                    block, target_columns, predicates, filter_cols_set, filter_fn
                )
                if was_skipped:
                    stats.blocks_skipped += 1
                    continue
                stats.blocks_scanned += 1
                stats.bytes_read += b_read
                stats.rows_scanned += block.row_count
                if batch is not None and batch.row_count > 0:
                    yield batch, stats

    def close(self):
        if getattr(self, "_mmap", None) is not None:
            try:
                self._mmap.close()
            except Exception:
                pass
            self._mmap = None
        if getattr(self, "_file", None) is not None and not self._file.closed:
            self._file.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
