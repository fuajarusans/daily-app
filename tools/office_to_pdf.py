"""Tool: Office to PDF — Word/Excel/PowerPoint -> PDF via LibreOffice headless.

LibreOffice ikut installer (folder vendor); di mode pengembang dipakai LibreOffice yang
terpasang. Konversi memakai profil LibreOffice milik Daily App dan berjalan satu per satu.
"""
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
    glyph = "file-type-pdf"
    hue = "#c2417f"
    accepted_extensions = [".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt", ".odt", ".ods", ".odp"]
    supports_batch = True
    options = []

    def check_dependencies(self) -> Optional[str]:
        if utils.find_libreoffice() is None:
            return (
                "Komponen LibreOffice tidak ditemukan. Pasang ulang Daily App dari installer "
                "terbaru (LibreOffice sudah termasuk di dalamnya)."
            )
        return None

    def process(self, input_paths, options, output_dir) -> list[Path]:
        soffice = utils.find_libreoffice()
        if not soffice:
            raise ToolError(self.check_dependencies() or "LibreOffice tidak ditemukan.")

        results: list[Path] = []
        for src in input_paths:
            try:
                out = utils.run_libreoffice_convert(soffice, src, output_dir)
            except subprocess.CalledProcessError as e:
                msg = e.stderr.decode(errors="ignore").strip() if e.stderr else ""
                raise ToolError(f"Gagal mengonversi '{src.name}'. {msg or 'Kode keluar ' + str(e.returncode)}")
            except subprocess.TimeoutExpired:
                raise ToolError(f"Konversi '{src.name}' terlalu lama (timeout).")

            if out is None:
                raise ToolError(
                    f"LibreOffice tidak menghasilkan PDF untuk '{src.name}'. "
                    "Pastikan file tidak rusak dan tidak sedang dibuka aplikasi lain."
                )
            results.append(out)
        return results
