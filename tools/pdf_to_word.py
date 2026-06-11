"""Tool: PDF ke Word (.pdf -> .docx) menggunakan pdf2docx."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from app.registry import Tool, ToolError, register_tool


@register_tool
class PdfToWordTool(Tool):
    id = "pdf-to-word"
    name = "PDF ke Word"
    description = "Konversi dokumen PDF menjadi file Word (.docx) yang bisa diedit."
    icon = "📄"
    accepted_extensions = [".pdf"]
    supports_batch = True
    options = []

    def process(self, input_paths, options, output_dir) -> list[Path]:
        try:
            from pdf2docx import Converter
        except ImportError:
            raise ToolError(
                "Library 'pdf2docx' belum terpasang. Jalankan: pip install pdf2docx"
            )

        results: list[Path] = []
        for src in input_paths:
            out = output_dir / f"{src.stem}.docx"
            try:
                cv = Converter(str(src))
                cv.convert(str(out))
                cv.close()
            except Exception as e:  # noqa: BLE001
                raise ToolError(f"Gagal mengonversi '{src.name}': {e}")
            results.append(out)
        return results
