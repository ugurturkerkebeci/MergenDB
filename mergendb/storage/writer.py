import os
import time
import struct
import json
from typing import List, Dict, Any, Union, Optional, Tuple
from mergendb.core.schema import Schema, ColumnDef
from mergendb.core.types import DataType, cast_value
from mergendb.core.block import ZoneMap, ColumnChunkMeta, BlockMeta
from mergendb.core.bloom import BlockBloomFilter
from mergendb.compression.compressor import ColumnCompressor
from mergendb.storage.format import MAGIC_HEADER, MAGIC_FOOTER, FORMAT_VERSION

class FileWriter:
    """
    Writes data in a columnar, compressed, block-indexed format (.mgdb).
    """

    def __init__(self, filepath: str, schema: Schema, block_size: int = 1024, auto_zlib: bool = True):
        self.filepath = filepath
        self.schema = schema
        self.block_size = block_size
        self.auto_zlib = auto_zlib

        self._file = open(filepath, "wb")
        self._block_meta_list: List[BlockMeta] = []
        self._current_buffer: Dict[str, List[Any]] = {col.name: [] for col in schema.columns}
        self._buffered_count = 0
        self._total_rows = 0
        self._block_counter = 0
        self._closed = False

        self._write_header()

    def _write_header(self):
        # Magic (4 bytes)
        self._file.write(MAGIC_HEADER)
        # Version (2 bytes) + Flags (2 bytes)
        self._file.write(struct.pack("<HH", FORMAT_VERSION, 0))
        # Created timestamp (8 bytes)
        self._file.write(struct.pack("<q", int(time.time() * 1000)))
        # Schema JSON
        schema_bytes = self.schema.to_json().encode("utf-8")
        self._file.write(struct.pack("<I", len(schema_bytes)))
        self._file.write(schema_bytes)

    def write_row(self, row: Union[Dict[str, Any], List[Any], Tuple[Any, ...]]):
        if self._closed:
            raise RuntimeError("Cannot write to a closed FileWriter.")

        if isinstance(row, dict):
            for col in self.schema.columns:
                val = row.get(col.name)
                cast_v = cast_value(val, col.data_type)
                self._current_buffer[col.name].append(cast_v)
        else:
            num_expected = len(self.schema.columns)
            row_len = len(row)
            for i, col in enumerate(self.schema.columns):
                val = row[i] if i < row_len else None
                cast_v = cast_value(val, col.data_type, safe=True)
                self._current_buffer[col.name].append(cast_v)


        self._buffered_count += 1
        self._total_rows += 1

        if self._buffered_count >= self.block_size:
            self._flush_block()

    def write_columns(self, col_data_map: Dict[str, List[Any]], count: int):
        """
        Writes data directly in columnar format for maximum throughput.
        col_data_map: mapping from column_name -> list of pre-cast values.
        count: number of rows represented.
        """
        if self._closed:
            raise RuntimeError("Cannot write to a closed FileWriter.")
        if count <= 0:
            return

        col_names = [col.name for col in self.schema.columns]
        for name in col_names:
            if name in col_data_map:
                self._current_buffer[name].extend(col_data_map[name])

        self._buffered_count += count
        self._total_rows += count

        while self._buffered_count >= self.block_size:
            excess = self._buffered_count - self.block_size
            if excess == 0:
                self._flush_block()
            else:
                saved = {}
                for name in col_names:
                    buf = self._current_buffer[name]
                    saved[name] = buf[self.block_size:]
                    self._current_buffer[name] = buf[:self.block_size]
                self._buffered_count = self.block_size
                self._flush_block()
                self._current_buffer = saved
                self._buffered_count = excess

    def write_rows(self, rows: List[Any]):
        if not rows:
            return
        if self._closed:
            raise RuntimeError("Cannot write to a closed FileWriter.")

        first = rows[0]
        if isinstance(first, (list, tuple)):
            col_names = [col.name for col in self.schema.columns]
            num_cols = len(col_names)
            cols_data = list(zip(*rows))
            for i in range(min(num_cols, len(cols_data))):
                col_def = self.schema.columns[i]
                vals = cols_data[i]
                cast_vals = [cast_value(v, col_def.data_type) for v in vals]
                self._current_buffer[col_names[i]].extend(cast_vals)

            n = len(rows)
            self._buffered_count += n
            self._total_rows += n

            while self._buffered_count >= self.block_size:
                excess = self._buffered_count - self.block_size
                if excess == 0:
                    self._flush_block()
                else:
                    saved = {}
                    for name in col_names:
                        buf = self._current_buffer[name]
                        saved[name] = buf[self.block_size:]
                        self._current_buffer[name] = buf[:self.block_size]
                    self._buffered_count = self.block_size
                    self._flush_block()
                    self._current_buffer = saved
                    self._buffered_count = excess
        else:
            for row in rows:
                self.write_row(row)

    def _flush_block(self):
        if self._buffered_count == 0:
            return

        col_chunks_meta: Dict[str, ColumnChunkMeta] = {}

        for col in self.schema.columns:
            values = self._current_buffer[col.name]
            compressed_bytes, enc_type, zone_map, uncomp_size = ColumnCompressor.compress(
                values, col.data_type, apply_zlib=self.auto_zlib
            )

            offset = self._file.tell()
            self._file.write(compressed_bytes)

            bloom = BlockBloomFilter.build_from_values(values) if col.data_type == DataType.STRING else None

            chunk_meta = ColumnChunkMeta(
                column_name=col.name,
                encoding=int(enc_type),
                offset=offset,
                compressed_bytes=len(compressed_bytes),
                uncompressed_bytes=uncomp_size,
                row_count=self._buffered_count,
                zone_map=zone_map,
                bloom_filter=bloom
            )
            col_chunks_meta[col.name] = chunk_meta

        block_meta = BlockMeta(
            block_id=self._block_counter,
            row_count=self._buffered_count,
            columns=col_chunks_meta
        )
        self._block_meta_list.append(block_meta)
        self._block_counter += 1

        # Reset buffer
        self._current_buffer = {col.name: [] for col in self.schema.columns}
        self._buffered_count = 0

    def close(self):
        if self._closed:
            return

        if self._buffered_count > 0:
            self._flush_block()

        # Write Footer
        footer_offset = self._file.tell()
        footer_data = {
            "total_rows": self._total_rows,
            "block_count": len(self._block_meta_list),
            "blocks": [b.to_dict() for b in self._block_meta_list]
        }
        footer_json_bytes = json.dumps(footer_data).encode("utf-8")
        self._file.write(footer_json_bytes)

        # Footer trailer: Footer size (uint32) + Footer Magic (4 bytes)
        self._file.write(struct.pack("<I", len(footer_json_bytes)))
        self._file.write(MAGIC_FOOTER)

        self._file.flush()
        self._file.close()
        self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
