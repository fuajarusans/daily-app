"""Tool: Hapus Watermark dari gambar (inpainting OpenCV).

UI tool ini BUKAN form generik, melainkan halaman kanvas kustom di `/watermark`
(lihat `app/watermark_routes.py` + `templates/watermark.html` + `static/watermark.js`).
Di sana pengguna menyapukan kuas / menarik kotak menutupi watermark; sapuan itu
diubah menjadi "mask" hitam-putih (PNG) lalu dikirim BERSAMA gambar asli ke
endpoint proses tool standar `/api/tool/watermark-remove/process`.

Karena memakai ulang endpoint standar, kontrak `process()` tetap dipatuhi:
`input_paths` berisi DUA file -> [gambar, mask]. `_split_inputs()` memisahkannya.

Catatan etis: gunakan hanya pada gambar milik Anda sendiri atau yang Anda berhak
menyuntingnya.

Dua engine tersedia (opsi `engine`):
  - "opencv" (default): cepat & ringan via `cv2.inpaint` (Telea/NS).
  - "lama": model AI LaMa (ONNX) via onnxruntime — lebih halus untuk area besar.
    Implementasi di `tools/_lama.py` (unduh model ~208 MB sekali pada pemakaian pertama).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from app.registry import Tool, ToolError, register_tool

# Petunjuk nama berkas mask yang dikirim oleh static/watermark.js.
MASK_HINT = "mask"


@register_tool
class WatermarkRemoveTool(Tool):
    id = "watermark-remove"
    name = "Hapus Watermark"
    description = (
        "Hapus watermark atau objek dari gambar dengan menyapukan kuas di atasnya "
        "(inpainting). Pilih engine cepat (OpenCV) atau lebih halus (LaMa AI). "
        "Buka tool untuk menandai area di kanvas."
    )
    icon = "🧽"
    # Halaman kustom berkanvas (lihat app/watermark_routes.py). Dashboard akan
    # menautkan kartu ke URL ini, bukan ke form generik /tool/<id>.
    custom_url = "/watermark"
    # Gambar asli + mask (PNG) sama-sama dikirim sebagai "files".
    accepted_extensions = [".png", ".jpg", ".jpeg", ".webp", ".bmp"]
    supports_batch = False
    requires_file = True
    options = [
        {
            "name": "engine",
            "label": "Engine",
            "type": "select",
            "choices": [
                {"value": "opencv", "label": "OpenCV — cepat & ringan"},
                {"value": "lama", "label": "LaMa (AI) — lebih halus, unduh model sekali (~208 MB)"},
            ],
            "default": "opencv",
        },
        {
            "name": "method",
            "label": "Metode inpaint (OpenCV)",
            "type": "select",
            "choices": [
                {"value": "telea", "label": "Telea (cepat, serbaguna)"},
                {"value": "ns", "label": "Navier-Stokes (lebih halus)"},
            ],
            "default": "telea",
        },
        {
            "name": "radius",
            "label": "Radius inpaint (OpenCV, px)",
            "type": "number",
            "min": 1,
            "max": 30,
            "default": 3,
        },
    ]

    def check_dependencies(self) -> str | None:
        try:
            import cv2  # noqa: F401
        except ImportError:
            return (
                "Library 'opencv-python-headless' belum terpasang. "
                "Jalankan: pip install opencv-python-headless"
            )
        return None

    def process(self, input_paths, options, output_dir) -> list[Path]:
        try:
            import cv2
            import numpy as np
        except ImportError:
            raise ToolError(
                "Library 'opencv-python-headless' belum terpasang. "
                "Jalankan: pip install opencv-python-headless"
            )

        image_path, mask_path = self._split_inputs(input_paths)

        engine = str(options.get("engine") or "opencv").lower()
        method = str(options.get("method") or "telea").lower()
        try:
            radius = int(options.get("radius") or 3)
        except (TypeError, ValueError):
            radius = 3
        radius = max(1, min(radius, 30))

        # imdecode/imencode + np.fromfile/write_bytes: aman untuk path Windows
        # yang mengandung spasi/karakter non-ASCII (cv2.imread bermasalah di situ).
        img = cv2.imdecode(np.fromfile(str(image_path), dtype=np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            raise ToolError(f"Gagal membaca gambar '{image_path.name}'.")

        mask = cv2.imdecode(np.fromfile(str(mask_path), dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
        if mask is None:
            raise ToolError(
                "Gagal membaca mask. Pastikan Anda menandai area watermark di kanvas."
            )

        # Kanvas frontend bisa berbeda ukuran dari gambar asli -> samakan dulu.
        if mask.shape[:2] != img.shape[:2]:
            mask = cv2.resize(
                mask, (img.shape[1], img.shape[0]), interpolation=cv2.INTER_NEAREST
            )

        # Binarkan: piksel terang (>127) = area yang ditandai untuk dihapus.
        _, mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)
        if cv2.countNonZero(mask) == 0:
            raise ToolError(
                "Area watermark belum ditandai. Sapukan kuas di atas watermark dulu, "
                "lalu tekan Proses."
            )

        # --- pemilihan engine ---
        if engine == "lama":
            result = self._inpaint_lama(img, mask)
        else:
            # OpenCV: lebarkan sedikit agar tepi watermark ikut tertutup rapi.
            mask_d = cv2.dilate(mask, np.ones((3, 3), np.uint8), iterations=1)
            flag = cv2.INPAINT_NS if method == "ns" else cv2.INPAINT_TELEA
            try:
                result = cv2.inpaint(img, mask_d, radius, flag)
            except cv2.error as e:  # noqa: BLE001
                raise ToolError(f"Gagal memproses inpaint: {e}")

        out = output_dir / f"{image_path.stem}_clean.png"
        ok, buf = cv2.imencode(".png", result)
        if not ok:
            raise ToolError("Gagal menyimpan hasil.")
        out.write_bytes(buf.tobytes())
        return [out]

    @staticmethod
    def _inpaint_lama(img, mask):
        """Jalankan engine LaMa (ONNX). Ubah kegagalan jadi ToolError yang ramah."""
        from tools import _lama

        if not _lama.onnxruntime_available():
            raise ToolError(
                "Engine LaMa membutuhkan 'onnxruntime' (biasanya sudah ikut terpasang "
                "via rembg). Jalankan: pip install onnxruntime"
            )
        try:
            return _lama.inpaint(img, mask)
        except RuntimeError as e:  # gagal mengunduh model
            raise ToolError(str(e))
        except Exception as e:  # noqa: BLE001
            raise ToolError(f"Gagal memproses dengan LaMa: {e}")

    @staticmethod
    def _split_inputs(input_paths: list[Path]) -> tuple[Path, Path]:
        """Pisahkan [gambar, mask] dari daftar input.

        Frontend mengirim dua file: gambar asli lebih dulu, lalu mask bernama
        'mask.png'. Utamakan deteksi via nama ('mask'); bila ambigu, jatuh ke
        urutan kirim (input_paths[0]=gambar, [1]=mask).
        """
        if len(input_paths) < 2:
            raise ToolError(
                "Butuh gambar DAN mask. Gunakan halaman tool (/watermark) untuk "
                "menandai area watermark — jangan mengunggah lewat form biasa."
            )
        masks = [p for p in input_paths if MASK_HINT in p.stem.lower()]
        images = [p for p in input_paths if p not in masks]
        if masks and images:
            return images[0], masks[0]
        # Fallback aman: pakai urutan kirim.
        return input_paths[0], input_paths[1]
