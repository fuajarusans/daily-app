"""Route halaman kustom "Hapus Watermark" (editor kanvas).

Modul ini HANYA menyajikan halaman HTML berisi kanvas untuk menandai watermark.
Proses inpainting-nya sendiri tetap memakai endpoint tool standar
`/api/tool/watermark-remove/process` (lihat tools/watermark_remove.py), sehingga
seluruh infrastruktur (job dir, pembersihan otomatis, /download) ikut terpakai.
"""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app import config
from app.registry import get_tool

router = APIRouter()
templates = Jinja2Templates(directory=str(config.TEMPLATE_DIR))


@router.get("/watermark", response_class=HTMLResponse)
async def watermark_page(request: Request):
    tool = get_tool("watermark-remove")
    if tool is None:
        return HTMLResponse("<h1>Tool tidak ditemukan</h1>", status_code=404)
    return templates.TemplateResponse(
        request, "watermark.html", {"tool": tool.to_dict()}
    )
