"""Tool: Hapus Background Gambar menggunakan rembg (model U²-Net).

Model u2net.onnx (~176 MB) ikut installer (folder vendor, lewat U2NET_HOME di config).
Di mode pengembang tanpa vendor, rembg mengunduhnya sekali ke ~/.u2net.

Sesi model dibuat sekali lalu dipakai ulang (hemat ~2 detik per gambar), dengan arena
memori onnxruntime dimatikan, dan dilepas setelah tidak dipakai selama
config.AI_IDLE_RELEASE_SECONDS. rembg dikunci di 2.0.75 (requirements.txt): versi
sesudahnya memakai model lain sebagai default (bria-rmbg, lisensi berbayar untuk komersial).
"""
from __future__ import annotations

import gc
import logging
import threading
from pathlib import Path

from app import config, utils
from app.registry import Tool, ToolError, register_tool

_session = None
_lock = threading.Lock()


def _release() -> None:
    global _session
    with _lock:
        _session = None
    gc.collect()


_idle = utils.IdleRelease(config.AI_IDLE_RELEASE_SECONDS, _release)


def _get_session():
    global _session
    with _lock:
        if _session is None:
            import onnxruntime as ort
            from rembg.sessions.u2net import U2netSession

            opts = ort.SessionOptions()
            opts.enable_cpu_mem_arena = False
            _session = U2netSession("u2net", opts)
        return _session


@register_tool
class RemoveBackgroundTool(Tool):
    id = "remove-background"
    name = "Hapus Background Gambar"
    description = "Hapus latar belakang gambar otomatis (AI). Hasil berupa PNG transparan."
    icon = "✂️"
    glyph = "background"
    hue = "#2f7fe0"
    accepted_extensions = [".png", ".jpg", ".jpeg", ".webp", ".bmp"]
    supports_batch = True
    options = []

    def process(self, input_paths, options, output_dir) -> list[Path]:
        # Selama diproses, model tidak dilepas; hitungan menganggur mulai setelah selesai.
        with _idle.in_use():
            return self._process(input_paths, output_dir)

    def _process(self, input_paths, output_dir) -> list[Path]:
        try:
            from rembg import remove
            session = _get_session()
        except ImportError:
            # Penyebab asli dicatat ke log: di exe, ImportError bisa berasal dari
            # dependency rembg (mis. metadata paket yang tidak ikut terbungkus).
            logging.getLogger(__name__).exception("Gagal mengimpor rembg")
            raise ToolError("Library 'rembg' belum terpasang. Jalankan: pip install rembg==2.0.75")
        except Exception as e:  # noqa: BLE001 - model hilang/rusak, gagal unduh di mode pengembang
            logging.getLogger(__name__).exception("Gagal memuat model Hapus Background")
            raise ToolError(f"Model AI Hapus Background tidak bisa dimuat: {e}")

        results: list[Path] = []
        for src in input_paths:
            try:
                output = remove(src.read_bytes(), session=session)
            except Exception as e:  # noqa: BLE001
                raise ToolError(f"Gagal memproses '{src.name}': {e}")
            out = output_dir / f"{src.stem}_nobg.png"
            out.write_bytes(output)
            results.append(out)
        return results
