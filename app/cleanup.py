"""Pembersihan otomatis file sementara agar tidak menumpuk."""
from __future__ import annotations

import asyncio
import shutil
import time

from app import config


def purge_old_files() -> int:
    """Hapus folder job di uploads/outputs yang lebih tua dari TTL.

    Kembalikan jumlah folder yang dihapus.
    """
    now = time.time()
    removed = 0
    for base in (config.UPLOAD_DIR, config.OUTPUT_DIR):
        if not base.exists():
            continue
        for child in base.iterdir():
            try:
                age = now - child.stat().st_mtime
                if age > config.FILE_TTL_SECONDS:
                    if child.is_dir():
                        shutil.rmtree(child, ignore_errors=True)
                    else:
                        child.unlink(missing_ok=True)
                    removed += 1
            except OSError:
                # File mungkin sedang dipakai; lewati dan coba lagi nanti.
                continue
    return removed


async def cleanup_loop() -> None:
    """Background task: jalankan pembersihan berkala selama aplikasi hidup."""
    while True:
        try:
            purge_old_files()
        except Exception:
            pass  # jangan sampai loop mati karena satu error
        await asyncio.sleep(config.CLEANUP_INTERVAL_SECONDS)
