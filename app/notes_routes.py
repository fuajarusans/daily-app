"""Route untuk fitur Catatan & Pengingat (dipisah dari main.py agar rapi)."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from app import config, notes_store, sticky_store
from app.templating import templates

router = APIRouter()
log = logging.getLogger(__name__)

_STICKY_COLORS = [
    {"id": c[0], "label": c[1], "bg": c[2], "ink": c[3], "muted": c[4], "focus": c[5]} for c in config.STICKY_COLORS
]
_NOT_FOUND = {"error": "Catatan tidak ditemukan."}


def _options() -> dict:
    """Pilihan yang dipakai halaman Catatan dan sticky (dari config, satu sumber)."""
    return {
        "categories": config.NOTE_CATEGORIES,
        "priorities": config.NOTE_PRIORITIES,
        "recurrences": [{"id": r["id"], "label": r["label"]} for r in config.NOTE_RECURRENCES],
    }


async def _body(request: Request) -> dict:
    try:
        data = await request.json()
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


@router.get("/notes", response_class=HTMLResponse)
async def notes_page(request: Request):
    return templates.TemplateResponse(request, "notes.html", _options())


@router.get("/api/notes")
async def api_list():
    return {
        "notes": notes_store.list_notes_sorted(),
        "archived": notes_store.list_archived(),
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
        return JSONResponse(_NOT_FOUND, status_code=404)
    return note


@router.get("/sticky/{note_id}", response_class=HTMLResponse)
async def sticky_page(request: Request, note_id: str):
    """Isi jendela sticky di desktop (halaman mandiri, tanpa base.html)."""
    if notes_store.get_note(note_id) is None:
        return HTMLResponse("Catatan tidak ditemukan.", status_code=404)
    return templates.TemplateResponse(
        request,
        "sticky.html",
        {"note_id": note_id, "sticky": sticky_store.get(note_id), "colors": _STICKY_COLORS, **_options()},
    )


@router.put("/api/stickies/{note_id}")
async def api_sticky_update(note_id: str, request: Request):
    """Simpan warna sticky (posisi & ukuran disimpan oleh jendela desktop sendiri)."""
    if notes_store.get_note(note_id) is None:
        return JSONResponse(_NOT_FOUND, status_code=404)
    data = await _body(request)
    return sticky_store.update(note_id, color=data.get("color"))


@router.post("/api/notes")
async def api_create(request: Request):
    data = await _body(request)
    items = data.get("checklist") if isinstance(data.get("checklist"), list) else []
    has_items = any(str((it.get("text") if isinstance(it, dict) else it) or "").strip() for it in items)
    if not (str(data.get("title") or "").strip() or str(data.get("body") or "").strip() or has_items):
        return JSONResponse(
            {"error": "Judul, isi, atau checklist catatan tidak boleh kosong."}, status_code=400
        )
    return notes_store.add_note(data)


@router.put("/api/notes/{note_id}")
async def api_update(note_id: str, request: Request):
    note = notes_store.update_note(note_id, await _body(request))
    if note is None:
        return JSONResponse(_NOT_FOUND, status_code=404)
    return note


@router.post("/api/notes/{note_id}/checklist")
async def api_checklist(note_id: str, request: Request):
    """Operasi checklist per item: {"ops": [{"op": "add"|"set"|"remove"|"move"|"clear_done", ...}]}."""
    data = await _body(request)
    note = notes_store.apply_checklist_ops(note_id, data.get("ops"))
    if note is None:
        return JSONResponse(_NOT_FOUND, status_code=404)
    return note


@router.post("/api/notes/{note_id}/undo")
async def api_undo(note_id: str):
    result = notes_store.undo(note_id)
    if result is None:
        return JSONResponse({"error": "Sudah tidak bisa diurungkan."}, status_code=410)
    note, sticky = result
    if sticky:
        try:
            sticky_store.restore(note_id, sticky)
        except OSError:  # catatan sudah dipulihkan; status sticky hanya pelengkap
            log.exception("Gagal memulihkan status sticky %s", note_id)
    return note


@router.delete("/api/notes/{note_id}")
async def api_delete(note_id: str):
    # Status sticky (posisi, warna) ikut disimpan agar "Urungkan" mengembalikannya utuh.
    sticky = sticky_store.raw(note_id)
    if not notes_store.delete_note(note_id, extra=sticky):
        return JSONResponse(_NOT_FOUND, status_code=404)
    try:
        sticky_store.remove(note_id)
    except OSError:
        # Catatan sudah terhapus (dan bisa diurungkan); entri sticky yang tertinggal dipangkas saat start.
        log.exception("Gagal menghapus status sticky %s", note_id)
    return {"ok": True}
