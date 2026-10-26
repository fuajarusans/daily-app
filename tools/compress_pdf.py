"""Tool: Compress PDF — perkecil ukuran file PDF.

Strategi:
  - Metode "Cepat (pikepdf)": kompres/linearize stream, buang objek tak terpakai.
    Selalu tersedia karena pikepdf adalah dependency pip.
  - Metode "Maksimal (Ghostscript)": re-encode gambar dengan target kualitas.
    Lebih efektif untuk PDF berisi banyak gambar. Ghostscript ikut installer
    (folder vendor); di mode pengembang dipakai Ghostscript yang terpasang.
    Bila hasilnya justru lebih besar dari aslinya, dicoba metode Cepat. Hasil akhir tidak
    pernah lebih besar dari file asli: bila tidak ada yang lebih kecil, file asli dikembalikan.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from app import utils
from app.registry import Tool, ToolError, register_tool

# Preset kualitas Ghostscript -> -dPDFSETTINGS
_GS_PRESETS = {
    "screen": "/screen",      # paling kecil (72 dpi)
    "ebook": "/ebook",        # seimbang (150 dpi)
    "printer": "/printer",    # kualitas tinggi (300 dpi)
}


@register_tool
class CompressPdfTool(Tool):
    id = "compress-pdf"
    name = "Compress PDF"
    description = "Perkecil ukuran file PDF. Metode 'Maksimal' mengompres ulang gambar di dalamnya."
    icon = "🗜️"
    glyph = "file-zip"
    hue = "#d64545"
    accepted_extensions = [".pdf"]
    supports_batch = True
    options = [
        {
            "name": "method",
            "label": "Metode kompresi",
            "type": "select",
            "choices": [
                {"value": "fast", "label": "Cepat (tanpa mengubah kualitas gambar)"},
                {"value": "max", "label": "Maksimal (Ghostscript, kompres ulang gambar)"},
            ],
            "default": "fast",
        },
        {
            "name": "quality",
            "label": "Kualitas (hanya untuk metode Maksimal)",
            "type": "select",
            "choices": [
                {"value": "screen", "label": "Kecil (screen, 72dpi)"},
                {"value": "ebook", "label": "Sedang (ebook, 150dpi)"},
                {"value": "printer", "label": "Tinggi (printer, 300dpi)"},
            ],
            "default": "ebook",
        },
    ]

    def _compress_pikepdf(self, src: Path, out: Path) -> None:
        try:
            import pikepdf
        except ImportError:
            raise ToolError(
                "Library 'pikepdf' belum terpasang. Jalankan: pip install pikepdf"
            )
        try:
            with pikepdf.open(str(src)) as pdf:
                pdf.save(
                    str(out),
                    compress_streams=True,
                    object_stream_mode=pikepdf.ObjectStreamMode.generate,
                    linearize=True,
                )
        except Exception as e:  # noqa: BLE001
            raise ToolError(f"Gagal mengompres '{src.name}': {e}")

    def _compress_ghostscript(self, src: Path, out: Path, preset: str) -> None:
        gs = utils.find_ghostscript()
        if not gs:
            raise ToolError(
                "Komponen Ghostscript tidak ditemukan. Pilih metode 'Cepat', atau pasang "
                "ulang Daily App dari installer terbaru."
            )
        setting = _GS_PRESETS.get(preset, "/ebook")
        cmd = [
            gs,
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4",
            f"-dPDFSETTINGS={setting}",
            "-dNOPAUSE",
            "-dQUIET",
            "-dBATCH",
            f"-sOutputFile={out}",
            str(src),
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=900,
                           env=utils.ghostscript_env(gs), **utils.no_window())
        except subprocess.CalledProcessError as e:
            msg = e.stderr.decode(errors="ignore") if e.stderr else str(e)
            raise ToolError(f"Ghostscript gagal pada '{src.name}': {msg}")
        except subprocess.TimeoutExpired:
            raise ToolError(f"Proses '{src.name}' terlalu lama (timeout).")

    def process(self, input_paths, options, output_dir) -> list[Path]:
        method = options.get("method", "fast")
        quality = options.get("quality", "ebook")

        results: list[Path] = []
        for src in input_paths:
            out = output_dir / f"{src.stem}_compressed.pdf"
            gs_tmp = output_dir / f"{src.stem}.gs.tmp"
            pk_tmp = output_dir / f"{src.stem}.pk.tmp"
            try:
                candidates: list[Path] = []
                if method == "max":
                    self._compress_ghostscript(src, gs_tmp, quality)
                    candidates.append(gs_tmp)
                    # PDF yang gambarnya sudah terkompres bisa justru membesar lewat Ghostscript.
                    if gs_tmp.stat().st_size >= src.stat().st_size:
                        try:
                            self._compress_pikepdf(src, pk_tmp)
                            candidates.append(pk_tmp)
                        except ToolError:
                            pass
                else:
                    self._compress_pikepdf(src, pk_tmp)
                    candidates.append(pk_tmp)
                best = min(candidates, key=lambda p: p.stat().st_size)
                if best.stat().st_size < src.stat().st_size:
                    os.replace(best, out)
                else:
                    shutil.copyfile(src, out)  # tidak ada yang lebih kecil: kembalikan aslinya
            finally:
                for tmp in (gs_tmp, pk_tmp):
                    tmp.unlink(missing_ok=True)
            results.append(out)
        return results
