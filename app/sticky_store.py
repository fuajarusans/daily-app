"""Penyimpanan status sticky note di desktop.

Satu berkas `data/stickies.json` berisi status per catatan: terbuka atau tidak, posisi,
ukuran, warna, dan "selalu di atas". Dipisah dari notes.json karena ini status tampilan
milik komputer ini (sering berubah saat sticky digeser) dan tidak boleh mengubah
`updated_at` catatan. Ditulis atomik (.tmp lalu os.replace) dan dilindungi lock.
"""
from __future__ import annotations

import json
import threading
from datetime import datetime
from typing import Any, Iterable, Optional

from app import config
from app.fileio import replace_with_retry

_LOCK = threading.RLock()
_COLOR_IDS = {c[0] for c in config.STICKY_COLORS}


def _read() -> dict:
    try:
        data = json.loads(config.STICKIES_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}
    items = data.get("stickies") if isinstance(data, dict) else None
    return items if isinstance(items, dict) else {}


def _write(items: dict) -> None:
    config.ensure_dirs()
    tmp = config.STICKIES_FILE.parent / (config.STICKIES_FILE.name + ".tmp")
    tmp.write_text(json.dumps({"version": 1, "stickies": items}, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    replace_with_retry(tmp, config.STICKIES_FILE)


def _int_or_none(value: Any) -> Optional[int]:
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return None


def _clean(item: dict) -> dict:
    w_min, h_min = config.STICKY_MIN_SIZE
    w_def, h_def = config.STICKY_DEFAULT_SIZE
    color = item.get("color")
    return {
        "open": bool(item.get("open", False)),
        "x": _int_or_none(item.get("x")),
        "y": _int_or_none(item.get("y")),
        "w": max(w_min, _int_or_none(item.get("w")) or w_def),
        "h": max(h_min, _int_or_none(item.get("h")) or h_def),
        "on_top": bool(item.get("on_top", False)),
        "color": color if color in _COLOR_IDS else config.STICKY_DEFAULT_COLOR,
    }


def get(note_id: str) -> dict:
    """Status sticky untuk satu catatan (default bila belum pernah dibuka)."""
    with _LOCK:
        return _clean(_read().get(note_id) or {})


def all_items() -> dict[str, dict]:
    with _LOCK:
        return {k: _clean(v) for k, v in _read().items() if isinstance(v, dict)}


def open_ids() -> list[str]:
    return [k for k, v in all_items().items() if v["open"]]


def update(note_id: str, **fields: Any) -> dict:
    """Ubah sebagian kolom (open, x, y, w, h, on_top, color) lalu simpan."""
    with _LOCK:
        items = _read()
        cur = _clean(items.get(note_id) or {})
        for key in ("open", "x", "y", "w", "h", "on_top", "color"):
            if key in fields and fields[key] is not None:
                cur[key] = fields[key]
        if fields.get("color") not in _COLOR_IDS:  # warna tak dikenal: pertahankan yang lama
            cur["color"] = _clean(items.get(note_id) or {})["color"]
        cur = _clean(cur)
        cur["updated_at"] = datetime.now().isoformat(timespec="seconds")
        items[note_id] = cur
        _write(items)
    return _clean(cur)


def remove(note_id: str) -> None:
    with _LOCK:
        items = _read()
        if items.pop(note_id, None) is not None:
            _write(items)


def raw(note_id: str) -> Optional[dict]:
    """Status tersimpan apa adanya (None bila belum pernah ditempel), untuk diurungkan."""
    with _LOCK:
        item = _read().get(note_id)
        return dict(item) if isinstance(item, dict) else None


def restore(note_id: str, item: dict) -> None:
    """Kembalikan status sticky yang disimpan raw() (urungkan hapus catatan)."""
    with _LOCK:
        items = _read()
        cur = _clean(item)
        cur["updated_at"] = datetime.now().isoformat(timespec="seconds")
        items[note_id] = cur
        _write(items)


def restorable_ids() -> list[str]:
    """Sticky berstatus terbuka yang catatannya masih ada dan tidak diarsipkan (untuk
    dipulihkan saat start). Status sticky catatan terarsip disimpan untuk saat dipulihkan."""
    try:
        notes = json.loads(config.NOTES_FILE.read_text(encoding="utf-8-sig"))
        valid = {n.get("id") for n in notes if isinstance(n, dict)}
        active = {n.get("id") for n in notes if isinstance(n, dict) and not n.get("archived")}
    except FileNotFoundError:
        valid = active = set()
    except (OSError, ValueError, AttributeError, TypeError):
        # notes.json tidak terbaca: jangan memangkas apa pun. Catatan yang hilang tetap
        # tertangani karena open_sticky menolak catatan yang tidak ada.
        return open_ids()
    prune(valid)
    return [i for i in open_ids() if i in active]


def prune(valid_ids: Iterable[str]) -> None:
    """Buang status sticky milik catatan yang sudah tidak ada."""
    keep = set(valid_ids)
    with _LOCK:
        items = _read()
        stale = [k for k in items if k not in keep]
        for k in stale:
            items.pop(k)
        if stale:
            _write(items)
