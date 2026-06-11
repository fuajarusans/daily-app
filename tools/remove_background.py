"""Tool: Hapus Background Gambar menggunakan rembg.

Catatan: rembg mengunduh model AI (~170 MB) saat PERTAMA kali dipakai,
jadi koneksi internet hanya dibutuhkan pada penggunaan pertama. Setelah model
ter-cache, tool berjalan sepenuhnya offline.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from app.registry import Tool, ToolError, register_tool


@register_tool
class RemoveBackgroundTool(Tool):
    id = "remove-background"
    name = "Hapus Background Gambar"
    description = (
        "Hapus latar belakang gambar otomatis (AI). Catatan: unduh model ~170MB "
        "saat pemakaian pertama (butuh internet sekali saja). Hasil berupa PNG transparan."
    )
    icon = "✂️"
    accepted_extensions = [".png", ".jpg", ".jpeg", ".webp", ".bmp"]
    supports_batch = True
    options = []

    def process(self, input_paths, options, output_dir) -> list[Path]:
        try:
            from rembg import remove
        except ImportError:
            raise ToolError(
                "Library 'rembg' belum terpasang. Jalankan: pip install rembg"
            )

        results: list[Path] = []
        for src in input_paths:
            try:
                data = src.read_bytes()
                output = remove(data)
            except Exception as e:  # noqa: BLE001
                raise ToolError(
                    f"Gagal memproses '{src.name}': {e}. "
                    "Bila ini pemakaian pertama, pastikan ada koneksi internet untuk "
                    "mengunduh model AI."
                )
            out = output_dir / f"{src.stem}_nobg.png"
            out.write_bytes(output)
            results.append(out)
        return results
