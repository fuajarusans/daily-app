"""Penulisan berkas JSON data pengguna (tanpa impor berat, aman dipakai saat start)."""
from __future__ import annotations

import os
import time


def replace_with_retry(tmp, target, attempts: int = 20) -> None:
    """os.replace (atomik) yang dicoba ulang: di Windows gagal dengan PermissionError selama
    berkas tujuan sedang dibuka thread/proses lain untuk dibaca."""
    for i in range(attempts):
        try:
            os.replace(tmp, target)
            return
        except PermissionError:
            if i == attempts - 1:
                raise
            time.sleep(0.02)
