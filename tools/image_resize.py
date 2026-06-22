"""Tool: Resize / Compress Gambar menggunakan Pillow. Mendukung batch.

Mode target ukuran: bila opsi `target_kb` > 0, tool MENGABAIKAN slider Kualitas
dan mencari kompresi secara otomatis (binary search kualitas) agar ukuran file
mendekati target tanpa melebihinya, dengan kualitas setinggi mungkin.
- JPG/WEBP (lossy): format dipertahankan, kualitas dicari otomatis.
- PNG/BMP/TIFF (lossless): dikonversi ke JPG (dimensi TETAP) agar bisa dikecilkan;
  transparansi diratakan ke latar putih.
"""
from __future__ import annotations

import io
from pathlib import Path
from typing import Any

from app.registry import Tool, ToolError, register_tool


@register_tool
class ImageResizeTool(Tool):
    id = "image-resize"
    name = "Resize / Compress Gambar"
    description = (
        "Ubah ukuran (persen atau lebar/tinggi), atur kualitas, atau tentukan "
        "target ukuran file (KB) untuk dikompres otomatis."
    )
    icon = "🖼️"
    accepted_extensions = [".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"]
    supports_batch = True
    options = [
        {
            "name": "mode",
            "label": "Metode ukuran",
            "type": "select",
            "choices": [
                {"value": "percent", "label": "Skala persen (%)"},
                {"value": "dimensions", "label": "Lebar/Tinggi (piksel)"},
                {"value": "none", "label": "Jangan ubah ukuran (kompres saja)"},
            ],
            "default": "percent",
        },
        {
            "name": "percent",
            "label": "Skala (%) — untuk mode persen",
            "type": "number",
            "min": 1,
            "max": 100,
            "default": 50,
        },
        {
            "name": "width",
            "label": "Lebar (px) — kosongkan untuk otomatis",
            "type": "number",
            "min": 0,
            "default": 0,
        },
        {
            "name": "height",
            "label": "Tinggi (px) — kosongkan untuk otomatis",
            "type": "number",
            "min": 0,
            "default": 0,
        },
        {
            "name": "quality",
            "label": "Kualitas (1-100, untuk JPG/WEBP) — diabaikan bila Target diisi",
            "type": "range",
            "min": 1,
            "max": 100,
            "default": 80,
        },
        {
            "name": "target_kb",
            "label": "Target ukuran file (KB) — 0 = nonaktif (PNG akan diubah ke JPG)",
            "type": "number",
            "min": 0,
            "default": 0,
        },
    ]

    # Batas pencarian kualitas untuk mode target.
    _QMIN = 5
    _QMAX = 95

    def process(self, input_paths, options, output_dir) -> list[Path]:
        try:
            from PIL import Image
        except ImportError:
            raise ToolError("Library 'Pillow' belum terpasang. Jalankan: pip install Pillow")

        mode = options.get("mode", "percent")
        percent = int(options.get("percent") or 50)
        width = int(options.get("width") or 0)
        height = int(options.get("height") or 0)
        quality = int(options.get("quality") or 80)
        try:
            target_kb = int(options.get("target_kb") or 0)
        except (TypeError, ValueError):
            target_kb = 0
        target_kb = max(0, target_kb)

        results: list[Path] = []
        for src in input_paths:
            try:
                img = Image.open(src)
            except Exception as e:  # noqa: BLE001
                raise ToolError(f"Gagal membuka '{src.name}': {e}")

            new_size = self._compute_size(img.size, mode, percent, width, height)
            if new_size != img.size:
                img = img.resize(new_size, Image.LANCZOS)

            try:
                if target_kb > 0:
                    out = self._save_to_target(img, src, output_dir, target_kb * 1024)
                else:
                    out = self._save_normal(img, src, output_dir, quality)
            except ToolError:
                raise
            except Exception as e:  # noqa: BLE001
                raise ToolError(f"Gagal menyimpan '{src.name}': {e}")
            results.append(out)
        return results

    # ------------------------------------------------------------------
    # Penyimpanan
    # ------------------------------------------------------------------
    def _save_normal(self, img, src: Path, output_dir: Path, quality: int) -> Path:
        """Perilaku lama: simpan dengan kualitas manual (atau optimize PNG)."""
        out = output_dir / f"{src.stem}_resized{src.suffix}"
        save_kwargs: dict[str, Any] = {}
        fmt = (img.format or src.suffix.lstrip(".")).upper()
        if fmt in ("JPEG", "JPG", "WEBP"):
            save_kwargs["quality"] = quality
            save_kwargs["optimize"] = True
            if img.mode in ("RGBA", "P") and fmt in ("JPEG", "JPG"):
                img = img.convert("RGB")
        elif fmt == "PNG":
            save_kwargs["optimize"] = True
        img.save(out, **save_kwargs)
        return out

    def _save_to_target(self, img, src: Path, output_dir: Path, target_bytes: int) -> Path:
        """Kompres mendekati target (best-effort), lalu tulis ke file.

        Nama file memuat ukuran tercapai, mis. 'foto_142KB.jpg'.
        """
        data, suffix = self._compress_to_target(img, src.suffix, target_bytes)
        achieved_kb = max(1, round(len(data) / 1024))
        out = output_dir / f"{src.stem}_{achieved_kb}KB{suffix}"
        out.write_bytes(data)
        return out

    # ------------------------------------------------------------------
    # Mesin pencarian target ukuran
    # ------------------------------------------------------------------
    def _compress_to_target(self, img, src_suffix: str, target_bytes: int) -> tuple[bytes, str]:
        """Cari kualitas tertinggi yang ukurannya <= target_bytes.

        JPG/WEBP: format dipertahankan. Format lain (PNG/BMP/TIFF): konversi ke JPG
        (dimensi tetap). Bila kualitas terendah pun masih > target, kembalikan hasil
        terkecil (best-effort) — dimensi tidak diubah.
        """
        fmt = (img.format or src_suffix.lstrip(".")).upper()
        if fmt == "WEBP":
            pil_format, suffix = "WEBP", ".webp"
        elif fmt in ("JPEG", "JPG"):
            pil_format, suffix = "JPEG", ".jpg"
        else:  # PNG/BMP/TIFF/lainnya -> JPG
            pil_format, suffix = "JPEG", ".jpg"

        if pil_format == "JPEG":
            img = self._flatten_to_rgb(img)

        def enc(q: int) -> bytes:
            kw: dict[str, Any] = {"quality": int(q)}
            if pil_format == "JPEG":
                kw["optimize"] = True
            elif pil_format == "WEBP":
                kw["method"] = 6
            return self._encode(img, pil_format, **kw)

        lo, hi = self._QMIN, self._QMAX
        best: bytes | None = None   # ukuran <= target, kualitas tertinggi
        smallest: bytes | None = None  # fallback bila tak ada yang <= target
        while lo <= hi:
            q = (lo + hi) // 2
            data = enc(q)
            if smallest is None or len(data) < len(smallest):
                smallest = data
            if len(data) <= target_bytes:
                best = data
                lo = q + 1   # coba kualitas lebih tinggi
            else:
                hi = q - 1   # terlalu besar, turunkan kualitas
        return (best if best is not None else smallest), suffix

    @staticmethod
    def _encode(img, pil_format: str, **kwargs) -> bytes:
        buf = io.BytesIO()
        img.save(buf, format=pil_format, **kwargs)
        return buf.getvalue()

    @staticmethod
    def _flatten_to_rgb(img):
        """Ratakan transparansi ke latar putih agar aman disimpan sebagai JPG."""
        from PIL import Image
        if img.mode == "RGB":
            return img
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            rgba = img.convert("RGBA")
            bg = Image.new("RGB", rgba.size, (255, 255, 255))
            bg.paste(rgba, mask=rgba.split()[-1])
            return bg
        return img.convert("RGB")

    @staticmethod
    def _compute_size(size, mode, percent, width, height):
        w, h = size
        if mode == "none":
            return (w, h)
        if mode == "percent":
            factor = max(1, percent) / 100.0
            return (max(1, int(w * factor)), max(1, int(h * factor)))
        # mode == "dimensions"
        if width and height:
            return (width, height)
        if width and not height:
            ratio = width / w
            return (width, max(1, int(h * ratio)))
        if height and not width:
            ratio = height / h
            return (max(1, int(w * ratio)), height)
        return (w, h)  # tidak ada dimensi diisi -> biarkan
