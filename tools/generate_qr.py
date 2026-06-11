"""Tool: Generate QR Code dari teks/URL menggunakan qrcode[pil]."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from app.registry import Tool, ToolError, register_tool


@register_tool
class GenerateQrTool(Tool):
    id = "generate-qr"
    name = "Generate QR Code"
    description = "Buat QR code dari teks atau URL, hasil berupa gambar PNG."
    icon = "🔳"
    accepted_extensions = []
    supports_batch = False
    requires_file = False  # tool ini tidak butuh upload file
    options = [
        {
            "name": "text",
            "label": "Teks atau URL",
            "type": "textarea",
            "default": "",
            "placeholder": "https://contoh.com atau teks apa pun",
        },
        {
            "name": "box_size",
            "label": "Ukuran modul (piksel per kotak)",
            "type": "number",
            "min": 2,
            "max": 40,
            "default": 10,
        },
        {
            "name": "border",
            "label": "Tebal border (kotak)",
            "type": "number",
            "min": 1,
            "max": 16,
            "default": 4,
        },
    ]

    def process(self, input_paths, options, output_dir) -> list[Path]:
        try:
            import qrcode
        except ImportError:
            raise ToolError(
                "Library 'qrcode' belum terpasang. Jalankan: pip install \"qrcode[pil]\""
            )

        text = (options.get("text") or "").strip()
        if not text:
            raise ToolError("Teks/URL tidak boleh kosong.")

        box_size = int(options.get("box_size") or 10)
        border = int(options.get("border") or 4)

        qr = qrcode.QRCode(box_size=box_size, border=border)
        qr.add_data(text)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        out = output_dir / "qrcode.png"
        img.save(out)
        return [out]
