"""Tool: Office to PDF — Word/Excel/PowerPoint -> PDF via LibreOffice headless."""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Optional

from app import utils
from app.registry import Tool, ToolError, register_tool


@register_tool
class OfficeToPdfTool(Tool):
    id = "office-to-pdf"
    name = "Office ke PDF"
    description = "Konversi Word/Excel/PowerPoint (.docx/.xlsx/.pptx) menjadi PDF."
    icon = "📑"
    accepted_extensions = [".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt", ".odt", ".ods", ".odp"]
    supports_batch = True
    options = []

    def check_dependencies(self) -> Optional[str]:
        if utils.find_libreoffice() is None:
            return (
                "LibreOffice belum terpasang. Tool ini memerlukan LibreOffice. "
                "Unduh di https://www.libreoffice.org/download/ lalu jalankan ulang "
                "aplikasi. (Detail di README bagian Dependency Eksternal.)"
            )
        return None

    def process(self, input_paths, options, output_dir) -> list[Path]:
        soffice = utils.find_libreoffice()
        if not soffice:
            raise ToolError(self.check_dependencies() or "LibreOffice tidak ditemukan.")

        results: list[Path] = []
        for src in input_paths:
            cmd = [
                soffice,
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                str(output_dir),
                str(src),
            ]
            try:
                subprocess.run(cmd, check=True, capture_output=True, timeout=300)
            except subprocess.CalledProcessError as e:
                msg = e.stderr.decode(errors="ignore") if e.stderr else str(e)
                raise ToolError(f"Gagal mengonversi '{src.name}': {msg}")
            except subprocess.TimeoutExpired:
                raise ToolError(f"Konversi '{src.name}' terlalu lama (timeout).")

            out = output_dir / f"{src.stem}.pdf"
            if not out.exists():
                raise ToolError(
                    f"LibreOffice tidak menghasilkan PDF untuk '{src.name}'. "
                    "Pastikan file tidak rusak dan tidak sedang dibuka aplikasi lain."
                )
            results.append(out)
        return results
