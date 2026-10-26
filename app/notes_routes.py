"""Route untuk fitur Catatan & Pengingat (dipisah dari main.py agar rapi)."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from app import config, notes_store, sticky_store
from app.templating import templates

router = APIRouter()

_STICKY_COLORS = [
    {"id": c[0], "label": c[1], "bg": c[2], "ink": c[3], "muted": c[4]} for c in config.STICKY_COLORS
]


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
    return {
        "notes": notes_store.list_notes_sorted(),
        "counts": notes_store.counts(),
        "stickies": sticky_store.open_ids(),
    }


@router.get("/api/notes/due")
async def api_due():
    return notes_store.due_payload()


# Didaftarkan setelah /api/notes/due agar "due" tidak dianggap id catatan.
@router.get("/api/notes/{note_id}")
async def api_get(note_id: str):
    note = notes_store.get_note(note_id)
    if note is None:
        return JSONResponse({"error": "Catatan tidak ditemukan."}, status_code=404)
    return note


@router.get("/sticky/{note_id}", response_class=HTMLResponse)
async def sticky_page(request: Request, note_id: str):
    """Isi jendela sticky di desktop (halaman mandiri, tanpa base.html)."""
    if notes_store.get_note(note_id) is None:
        return HTMLResponse("Catatan tidak ditemukan.", status_code=404)
    return templates.TemplateResponse(
        request,
        "sticky.html",
        {
            "note_id": note_id,
            "sticky": sticky_store.get(note_id),
            "colors": _STICKY_COLORS,
            "categories": config.NOTE_CATEGORIES,
        },
    )


@router.put("/api/stickies/{note_id}")
async def api_sticky_update(note_id: str, request: Request):
    """Simpan warna sticky (posisi & ukuran disimpan oleh jendela desktop sendiri)."""
    if notes_store.get_note(note_id) is None:
        return JSONResponse({"error": "Catatan tidak ditemukan."}, status_code=404)
    data = await request.json()
    return sticky_store.update(note_id, color=data.get("color"))


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
    sticky_store.remove(note_id)
    return {"ok": True}
