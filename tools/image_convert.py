"""Tool: Convert Format Gambar (PNG/JPG/WEBP/HEIC, dll) via Pillow + pillow-heif."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from app.registry import Tool, ToolError, register_tool

# Daftarkan dukungan HEIC bila pillow-heif tersedia.
try:
    import pillow_heif  # type: ignore

    pillow_heif.register_heif_opener()
    _HEIF_OK = True
except ImportError:
    _HEIF_OK = False


# Pemetaan format target -> (ekstensi, format Pillow)
_TARGETS = {
    "png": (".png", "PNG"),
    "jpg": (".jpg", "JPEG"),
    "webp": (".webp", "WEBP"),
    "bmp": (".bmp", "BMP"),
    "tiff": (".tiff", "TIFF"),
}


@register_tool
class ImageConvertTool(Tool):
    id = "image-convert"
    name = "Convert Format Gambar"
    description = "Ubah format gambar antar PNG / JPG / WEBP / HEIC / BMP / TIFF. Mendukung batch."
    icon = "🔄"
    accepted_extensions = [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".heic", ".heif"]
    supports_batch = True
    options = [
        {
            "name": "target",
            "label": "Format tujuan",
            "type": "select",
            "choices": [
                {"value": "png", "label": "PNG"},
                {"value": "jpg", "label": "JPG"},
                {"value": "webp", "label": "WEBP"},
                {"value": "bmp", "label": "BMP"},
                {"value": "tiff", "label": "TIFF"},
            ],
            "default": "png",
        },
        {
            "name": "quality",
            "label": "Kualitas (untuk JPG/WEBP)",
            "type": "range",
            "min": 1,
            "max": 100,
            "default": 90,
        },
    ]

    def process(self, input_paths, options, output_dir) -> list[Path]:
        try:
            from PIL import Image
        except ImportError:
            raise ToolError("Library 'Pillow' belum terpasang. Jalankan: pip install Pillow")

        target = options.get("target", "png")
        quality = int(options.get("quality") or 90)
        ext, pil_format = _TARGETS.get(target, (".png", "PNG"))

        results: list[Path] = []
        for src in input_paths:
            if src.suffix.lower() in (".heic", ".heif") and not _HEIF_OK:
                raise ToolError(
                    "File HEIC terdeteksi tetapi 'pillow-heif' belum terpasang. "
                    "Jalankan: pip install pillow-heif"
                )
            try:
                img = Image.open(src)
            except Exception as e:  # noqa: BLE001
                raise ToolError(f"Gagal membuka '{src.name}': {e}")

            # JPG/BMP tidak mendukung alpha -> konversi ke RGB
            if pil_format in ("JPEG", "BMP") and img.mode in ("RGBA", "P", "LA"):
                img = img.convert("RGB")

            out = output_dir / f"{src.stem}{ext}"
            save_kwargs: dict[str, Any] = {}
            if pil_format in ("JPEG", "WEBP"):
                save_kwargs["quality"] = quality
            try:
                img.save(out, format=pil_format, **save_kwargs)
            except Exception as e:  # noqa: BLE001
                raise ToolError(f"Gagal mengonversi '{src.name}': {e}")
            results.append(out)
        return results
