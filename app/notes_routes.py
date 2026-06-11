"""Route untuk fitur Catatan & Pengingat (dipisah dari main.py agar rapi)."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app import config, notes_store

router = APIRouter()
templates = Jinja2Templates(directory=str(config.TEMPLATE_DIR))


@router.get("/notes", response_class=HTMLResponse)
async def notes_page(request: Request):
    return templates.TemplateResponse(
        request,
        "notes.html",
        {
            "counts": notes_store.counts(),
            "all_tags": notes_store.all_tags(),
            "categories": config.NOTE_CATEGORIES,
        },
    )


@router.get("/api/notes")
async def api_list():
    return {"notes": notes_store.list_notes_sorted(), "counts": notes_store.counts()}


@router.get("/api/notes/due")
async def api_due():
    return notes_store.due_payload()


@router.post("/api/notes")
async def api_create(request: Request):
    data = await request.json()
    if not (str(data.get("title") or "").strip() or str(data.get("body") or "").strip()):
        return JSONResponse(
            {"error": "Judul atau isi catatan tidak boleh kosong."}, status_code=400
        )
    return notes_store.add_note(data)


@router.put("/api/notes/{note_id}")
async def api_update(note_id: str, request: Request):
    data = await request.json()
    note = notes_store.update_note(note_id, data)
    if note is None:
        return JSONResponse({"error": "Catatan tidak ditemukan."}, status_code=404)
    return note


@router.delete("/api/notes/{note_id}")
async def api_delete(note_id: str):
    if not notes_store.delete_note(note_id):
        return JSONResponse({"error": "Catatan tidak ditemukan."}, status_code=404)
    return {"ok": True}
