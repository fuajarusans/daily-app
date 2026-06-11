"""Penyimpanan Catatan & Pengingat.

Disimpan permanen di `data/notes.json` (di luar area auto-cleanup). Tanpa database:
cukup satu berkas JSON, ditulis secara atomik (tulis ke .tmp lalu os.replace) dan
dilindungi lock agar aman dari penulisan bersamaan.
"""
from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import date, datetime, timedelta
from typing import Any, Optional

from app import config

_LOCK = threading.Lock()

# Urutan prioritas status untuk pengurutan daftar.
_STATUS_ORDER = {
    "overdue": 0,    # sudah lewat tempo
    "today": 1,      # jatuh tempo hari ini
    "soon": 2,       # akan datang (dalam ambang H-n)
    "scheduled": 3,  # punya tanggal, masih jauh
    "none": 4,       # tanpa tanggal
    "done": 5,       # selesai
}


# ---------------------------------------------------------------------------
# Baca / tulis berkas
# ---------------------------------------------------------------------------
def _ensure_file() -> None:
    config.ensure_dirs()
    if not config.NOTES_FILE.exists():
        config.NOTES_FILE.write_text("[]", encoding="utf-8")


def _read_raw() -> list[dict]:
    _ensure_file()
    try:
        data = json.loads(config.NOTES_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _write_raw(notes: list[dict]) -> None:
    config.ensure_dirs()
    tmp = config.NOTES_FILE.parent / (config.NOTES_FILE.name + ".tmp")
    tmp.write_text(json.dumps(notes, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, config.NOTES_FILE)  # penggantian atomik


# ---------------------------------------------------------------------------
# Util
# ---------------------------------------------------------------------------
def _now() -> datetime:
    return datetime.now()


def _to_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _valid_category(value: Any) -> str:
    cat = str(value).strip() if value else ""
    ids = {c["id"] for c in config.NOTE_CATEGORIES}
    return cat if cat in ids else config.DEFAULT_NOTE_CATEGORY


def _normalize_tags(tags: Any) -> list[str]:
    if isinstance(tags, str):
        items = tags.split(",")
    elif isinstance(tags, (list, tuple)):
        items = tags
    else:
        items = []
    out: list[str] = []
    for t in items:
        s = str(t).strip()
        if s and s not in out:
            out.append(s)
    return out


def _parse_due(due: Optional[str]) -> Optional[datetime]:
    """Terima 'YYYY-MM-DD' atau 'YYYY-MM-DDTHH:MM'. Tanggal-saja dianggap akhir hari."""
    if not due:
        return None
    s = str(due).strip()
    try:
        if "T" in s:
            return datetime.fromisoformat(s)
        d = date.fromisoformat(s)
        return datetime(d.year, d.month, d.day, 23, 59, 59)
    except ValueError:
        return None


def compute_status(note: dict) -> str:
    if note.get("done"):
        return "done"
    due_dt = _parse_due(note.get("due"))
    if due_dt is None:
        return "none"
    now = _now()
    if due_dt.date() == now.date():
        return "today"
    if due_dt < now:
        return "overdue"
    lead = _to_int(note.get("remind_before_days"), config.REMINDER_DEFAULT_LEAD_DAYS)
    if now >= (due_dt - timedelta(days=lead)):
        return "soon"
    return "scheduled"


def _annotate(note: dict) -> dict:
    m = dict(note)
    m["status"] = compute_status(note)
    m.setdefault("category", config.DEFAULT_NOTE_CATEGORY)
    return m


def _sort_key(note: dict):
    done = 1 if note.get("done") else 0
    pinned = 0 if note.get("pinned") else 1
    rank = _STATUS_ORDER.get(note.get("status", "none"), 4)
    due_dt = _parse_due(note.get("due"))
    due_rank = due_dt.timestamp() if due_dt else float("inf")
    return (done, pinned, rank, due_rank, note.get("created_at", ""))


# ---------------------------------------------------------------------------
# Operasi publik
# ---------------------------------------------------------------------------
def list_notes() -> list[dict]:
    return [_annotate(n) for n in _read_raw()]


def list_notes_sorted() -> list[dict]:
    return sorted(list_notes(), key=_sort_key)


def get_note(note_id: str) -> Optional[dict]:
    for n in _read_raw():
        if n.get("id") == note_id:
            return _annotate(n)
    return None


def add_note(data: dict) -> dict:
    now_iso = _now().isoformat(timespec="seconds")
    note = {
        "id": uuid.uuid4().hex,
        "title": (data.get("title") or "").strip(),
        "body": (data.get("body") or "").strip(),
        "tags": _normalize_tags(data.get("tags")),
        "category": _valid_category(data.get("category")),
        "pinned": bool(data.get("pinned", False)),
        "done": bool(data.get("done", False)),
        "due": ((data.get("due") or "").strip() or None),
        "remind_before_days": _to_int(
            data.get("remind_before_days"), config.REMINDER_DEFAULT_LEAD_DAYS
        ),
        "created_at": now_iso,
        "updated_at": now_iso,
    }
    with _LOCK:
        notes = _read_raw()
        notes.append(note)
        _write_raw(notes)
    return _annotate(note)


def update_note(note_id: str, data: dict) -> Optional[dict]:
    with _LOCK:
        notes = _read_raw()
        for n in notes:
            if n.get("id") != note_id:
                continue
            if "title" in data:
                n["title"] = (data.get("title") or "").strip()
            if "body" in data:
                n["body"] = (data.get("body") or "").strip()
            if "tags" in data:
                n["tags"] = _normalize_tags(data.get("tags"))
            if "category" in data:
                n["category"] = _valid_category(data.get("category"))
            if "pinned" in data:
                n["pinned"] = bool(data.get("pinned"))
            if "done" in data:
                n["done"] = bool(data.get("done"))
            if "due" in data:
                n["due"] = (data.get("due") or "").strip() or None
            if "remind_before_days" in data:
                n["remind_before_days"] = _to_int(
                    data.get("remind_before_days"), config.REMINDER_DEFAULT_LEAD_DAYS
                )
            n["updated_at"] = _now().isoformat(timespec="seconds")
            _write_raw(notes)
            return _annotate(n)
    return None


def delete_note(note_id: str) -> bool:
    with _LOCK:
        notes = _read_raw()
        remaining = [n for n in notes if n.get("id") != note_id]
        if len(remaining) == len(notes):
            return False
        _write_raw(remaining)
        return True


def all_tags() -> list[str]:
    tags: list[str] = []
    for n in _read_raw():
        for t in _normalize_tags(n.get("tags")):
            if t not in tags:
                tags.append(t)
    return sorted(tags, key=str.lower)


def counts() -> dict:
    c = {"overdue": 0, "today": 0, "soon": 0, "open": 0, "done": 0, "total": 0}
    for n in list_notes():
        c["total"] += 1
        s = n["status"]
        if s in ("overdue", "today", "soon"):
            c[s] += 1
        if n.get("done"):
            c["done"] += 1
        else:
            c["open"] += 1
    c["badge"] = c["overdue"] + c["today"]
    return c


def due_payload() -> dict:
    """Ringkasan untuk lencana header & notifikasi browser (dipanggil berkala)."""
    items = [
        {"id": n["id"], "title": n["title"] or "(tanpa judul)", "status": n["status"]}
        for n in list_notes_sorted()
        if n["status"] in ("overdue", "today")
    ]
    c = counts()
    return {
        "badge": c["badge"],
        "overdue": c["overdue"],
        "today": c["today"],
        "soon": c["soon"],
        "items": items,
    }
