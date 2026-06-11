"""Tool: Resize / Compress Gambar menggunakan Pillow. Mendukung batch."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from app.registry import Tool, ToolError, register_tool


@register_tool
class ImageResizeTool(Tool):
    id = "image-resize"
    name = "Resize / Compress Gambar"
    description = "Ubah ukuran (persen atau lebar/tinggi) dan atur kualitas untuk memperkecil file."
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
            "label": "Kualitas (1-100, untuk JPG/WEBP)",
            "type": "range",
            "min": 1,
            "max": 100,
            "default": 80,
        },
    ]

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

        results: list[Path] = []
        for src in input_paths:
            try:
                img = Image.open(src)
            except Exception as e:  # noqa: BLE001
                raise ToolError(f"Gagal membuka '{src.name}': {e}")

            new_size = self._compute_size(img.size, mode, percent, width, height)
            if new_size != img.size:
                img = img.resize(new_size, Image.LANCZOS)

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

            try:
                img.save(out, **save_kwargs)
            except Exception as e:  # noqa: BLE001
                raise ToolError(f"Gagal menyimpan '{src.name}': {e}")
            results.append(out)
        return results

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
