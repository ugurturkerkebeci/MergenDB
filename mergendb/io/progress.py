import sys
import time
from typing import Optional

class ProgressBar:
    """
    High-performance, cross-platform terminal progress bar for MergenDB.
    - Zero dependencies.
    - 100% safe on Turkish Windows (cp1254), Windows (cp1252/cp437), Linux, macOS, and Docker.
    - Displays exact percentage (0.0% to 100.0%), row count, transfer speed (rows/s), and ETA.
    - Uses minimal CPU overhead with adaptive throttling (updates max 5 times/second).
    """

    def __init__(
        self,
        action: str = "Processing",
        total_rows: Optional[int] = None,
        total_bytes: Optional[int] = None,
        bar_width: int = 24
    ):
        self.action = action
        self.total_rows = total_rows
        self.total_bytes = total_bytes
        self.bar_width = bar_width
        self.start_time = time.time()
        self.last_update = 0.0
        self.current_rows = 0

    def update(self, current_rows: int, current_bytes: Optional[int] = None, force: bool = False):
        self.current_rows = current_rows
        now = time.time()
        if not force and (now - self.last_update < 0.20):
            return

        self.last_update = now
        elapsed = max(now - self.start_time, 0.001)
        speed = current_rows / elapsed

        pct = 0.0
        eta_str = "--s"

        if self.total_rows and self.total_rows > 0:
            pct = min(100.0, (current_rows / self.total_rows) * 100.0)
            remaining_rows = max(0, self.total_rows - current_rows)
            eta = remaining_rows / max(speed, 1.0)
            eta_str = f"{eta:.0f}s"
        elif self.total_bytes and current_bytes is not None and self.total_bytes > 0:
            pct = min(100.0, (current_bytes / self.total_bytes) * 100.0)
            byte_rate = current_bytes / elapsed
            remaining_bytes = max(0, self.total_bytes - current_bytes)
            eta = remaining_bytes / max(byte_rate, 1.0)
            eta_str = f"{eta:.0f}s"

        filled = int(self.bar_width * (pct / 100.0))
        if filled >= self.bar_width:
            bar = "=" * self.bar_width
        else:
            bar = ("=" * filled + ">").ljust(self.bar_width, "-")

        if self.total_rows and self.total_rows > 0:
            msg = f"\r[*] {self.action}: {current_rows:,} / {self.total_rows:,} rows [{bar}] {pct:5.1f}% | {speed:,.0f} rows/s | ETA: {eta_str}  "
        else:
            msg = f"\r[*] {self.action}: {current_rows:,} rows [{bar}] {pct:5.1f}% | {speed:,.0f} rows/s | ETA: {eta_str}  "

        sys.stdout.write(msg)
        sys.stdout.flush()

    def finish(self, final_msg: Optional[str] = None):
        self.update(self.current_rows, self.total_bytes, force=True)
        elapsed = max(time.time() - self.start_time, 0.001)
        speed = self.current_rows / elapsed
        if final_msg:
            sys.stdout.write(f"\r{final_msg.ljust(90)}\n")
        else:
            sys.stdout.write(f"\r[+] {self.action} complete: {self.current_rows:,} rows in {elapsed:.2f}s ({speed:,.0f} rows/s)           \n")
        sys.stdout.flush()
