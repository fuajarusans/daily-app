"""Desain PDF invoice — satu file = satu desain (auto-terdaftar).

Menambah desain baru: buat file `.py` di folder ini berisi subclass `InvoiceDesign`
dengan decorator `@register_design` (lihat `klasik.py` sebagai contoh paling sederhana).
File berawalan `_` tidak di-auto-import.
"""
from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path
from typing import Optional

from app import config
from app.invoice_designs._base import Ctx, Doc, all_designs, get_design, hex_rgb

# Pakai __path__ (bukan path folder): di exe PyInstaller modul ada di arsip, bukan file.
for _m in pkgutil.iter_modules(__path__):
    if not _m.name.startswith("_"):
        importlib.import_module(f"{__name__}.{_m.name}")


def render_pdf(inv: dict, profile: dict, logo: Optional[Path] = None) -> bytes:
    """Render invoice (sudah di-annotate, punya `totals`) menjadi bytes PDF."""
    design = (
        get_design(inv.get("design") or "")
        or get_design(profile.get("design") or "")
        or get_design(config.INVOICE_DEFAULT_DESIGN)
        or all_designs()[0]
    )
    color = design.default_color
    if design.uses_accent:
        color = inv.get("accent_color") or profile.get("accent_color") or design.default_color
    ctx = Ctx(profile=profile, inv=inv, accent=hex_rgb(color, design.default_color), logo=logo)
    doc = Doc(ctx)
    design.setup(doc)
    doc.add_page()
    design.render(doc)
    return bytes(doc.output())


__all__ = ["render_pdf", "all_designs", "get_design"]
