"""Penyimpanan Catatan & Pengingat.

Disimpan permanen di `data/notes.json` (di luar area auto-cleanup). Tanpa database:
cukup satu berkas JSON, ditulis secara atomik (tulis ke .tmp lalu os.replace) dan
dilindungi lock agar aman dari penulisan bersamaan.

Kolom baru (1.4) ditambahkan tanpa migrasi: catatan lama tetap terbaca, nilai bawaannya
diisi saat dibaca (_annotate). notes.json tetap berupa list agar versi lama tidak salah baca.
"""
from __future__ import annotations

import calendar
import json
import logging
import re
import shutil
import threading
import time
import uuid
from datetime import date, datetime, timedelta
from typing import Any, Optional

from app import config
from app.fileio import replace_with_retry

log = logging.getLogger(__name__)

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
_PRIORITY_RANK = {p["id"]: i for i, p in enumerate(config.NOTE_PRIORITIES)}
_RECUR_DAYS = {r["id"]: r["days"] for r in config.NOTE_RECURRENCES}
_ITEM_ID = re.compile(r"[0-9a-z]{6,32}")

# Urungkan (hapus, arsipkan, selesai-berulang): id catatan -> keadaan sebelum aksi terakhir.
# Hanya di memori dan hanya diakses sambil memegang _LOCK.
_UNDO: dict[str, dict] = {}
_corrupt_sig: Optional[tuple] = None


# ---------------------------------------------------------------------------
# Baca / tulis berkas
# ---------------------------------------------------------------------------
def _ensure_file() -> None:
    config.ensure_dirs()
    if not config.NOTES_FILE.exists():
        config.NOTES_FILE.write_text("[]", encoding="utf-8")


def _backup_corrupt() -> None:
    """Salin notes.json yang rusak (sekali per isi) sebelum tertimpa penulisan berikutnya."""
    global _corrupt_sig
    try:
        st = config.NOTES_FILE.stat()
        sig = (st.st_size, st.st_mtime_ns)
        if sig == _corrupt_sig:
            return
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        dst = config.NOTES_FILE.with_name(f"notes.rusak-{stamp}.json")
        shutil.copy2(config.NOTES_FILE, dst)
        _corrupt_sig = sig
        log.error("notes.json tidak terbaca; salinannya disimpan di %s", dst)
    except OSError:
        log.exception("Gagal menyalin notes.json yang rusak")


def _read_raw(strict: bool = False) -> list[dict]:
    """Baca notes.json.

    strict=True dipakai sebelum menulis: berkas yang gagal dibaca menjadi error, bukan
    daftar kosong, agar catatan tidak tertimpa habis hanya karena berkas sedang terkunci.
    """
    _ensure_file()
    text = None
    for _ in range(10):
        try:
            # utf-8-sig: berkas yang disimpan ulang dengan BOM (mis. lewat Notepad) tetap terbaca.
            text = config.NOTES_FILE.read_text(encoding="utf-8-sig")
            break
        except UnicodeDecodeError:
            _backup_corrupt()
            return []
        except PermissionError:
            # Sedang diganti os.replace oleh thread lain (Windows): coba sebentar lagi.
            time.sleep(0.02)
        except OSError:
            if strict:
                raise
            return []
    if text is None:
        if strict:
            raise OSError("notes.json sedang dipakai proses lain")
        return []
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        _backup_corrupt()
        return []
    if not isinstance(data, list):
        _backup_corrupt()
        return []
    return [n for n in data if isinstance(n, dict)]


def _write_raw(notes: list[dict]) -> None:
    config.ensure_dirs()
    tmp = config.NOTES_FILE.parent / (config.NOTES_FILE.name + ".tmp")
    tmp.write_text(json.dumps(notes, ensure_ascii=False, indent=2), encoding="utf-8")
    # Penggantian atomik; dicoba ulang bila notes.json sedang dibaca thread lain (sticky
    # menyimpan otomatis sambil halaman Catatan memuat daftar).
    replace_with_retry(tmp, config.NOTES_FILE)


# ---------------------------------------------------------------------------
# Util
# ---------------------------------------------------------------------------
def _now() -> datetime:
    return datetime.now()


def _now_iso() -> str:
    return _now().isoformat(timespec="seconds")


def _to_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):  # OverflowError: Infinity/1e400 dari JSON
        return default


def _valid_category(value: Any) -> str:
    cat = str(value).strip() if value else ""
    ids = {c["id"] for c in config.NOTE_CATEGORIES}
    return cat if cat in ids else config.DEFAULT_NOTE_CATEGORY


def _valid_priority(value: Any) -> Optional[str]:
    p = str(value).strip().lower() if value else ""
    return p if p in _PRIORITY_RANK else None


def _valid_recurrence(value: Any) -> Optional[str]:
    r = str(value).strip().lower() if value else ""
    return r if r in _RECUR_DAYS else None


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
            return datetime.fromisoformat(s).replace(tzinfo=None)
        d = date.fromisoformat(s)
        return datetime(d.year, d.month, d.day, 23, 59, 59)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Checklist: daftar datar [{id, text, done, priority, level}]. Sub-item = level 1 yang
# mengikuti item level 0 di atasnya. Daftar datar memudahkan pindah & ubah tingkat.
# ---------------------------------------------------------------------------
def _clean_text(value: Any) -> str:
    text = str(value if value is not None else "").replace("\r", " ").replace("\n", " ").replace("\t", " ")
    return text.strip()[: config.CHECKLIST_TEXT_MAX]


def _clamp_level(value: Any) -> int:
    return min(max(_to_int(value, 0), 0), config.CHECKLIST_MAX_LEVEL)


def _new_item_id(taken: set) -> str:
    while True:
        iid = uuid.uuid4().hex[:12]
        if iid not in taken:
            return iid


def _normalize_checklist(items: Any, keep_empty: bool = False) -> list[dict]:
    """Bersihkan daftar dari klien/berkas. Item kosong dibuang, kecuali yang tersimpan
    (keep_empty): baris baru memang kosong sesaat sebelum diketik."""
    out: list[dict] = []
    if not isinstance(items, (list, tuple)):
        return out
    taken: set = set()
    for raw in items:
        if len(out) >= config.CHECKLIST_MAX_ITEMS:
            break
        if isinstance(raw, str):
            raw = {"text": raw}
        if not isinstance(raw, dict):
            continue
        text = _clean_text(raw.get("text"))
        if not text and not keep_empty:
            continue
        iid = str(raw.get("id") or "")
        if not _ITEM_ID.fullmatch(iid) or iid in taken:
            iid = _new_item_id(taken)
        taken.add(iid)
        out.append({
            "id": iid,
            "text": text,
            "done": bool(raw.get("done", False)),
            "priority": _valid_priority(raw.get("priority")),
            "level": _clamp_level(raw.get("level")) if out else 0,
        })
    return out


def _subtree_end(items: list[dict], idx: int) -> int:
    """Indeks tepat setelah item idx beserta sub-item di bawahnya."""
    end = idx + 1
    if items[idx]["level"] == 0:
        while end < len(items) and items[end]["level"] > 0:
            end += 1
    return end


def _sid(value: Any) -> Optional[str]:
    """Id item hanya berupa teks; tipe lain (list/objek/angka) dianggap tidak ada."""
    return value if isinstance(value, str) else None


def _apply_op(items: list[dict], op: dict) -> None:
    """Satu operasi checklist. Item yang sudah tidak ada (dihapus di jendela lain) diabaikan."""
    kind = op.get("op")
    pos = {it["id"]: i for i, it in enumerate(items)}
    oid = _sid(op.get("id"))
    if kind == "add":
        if len(items) >= config.CHECKLIST_MAX_ITEMS:
            return
        iid = oid or ""
        if not _ITEM_ID.fullmatch(iid) or iid in pos:
            iid = _new_item_id(set(pos))
        level = _clamp_level(op.get("level"))
        after = _sid(op.get("after"))
        if after in pos:
            idx = pos[after]
            if level > 0:
                at = idx + 1
            else:
                # Item baru level 0 diletakkan setelah sub-item milik induknya.
                parent = idx
                while parent > 0 and items[parent]["level"] > 0:
                    parent -= 1
                at = _subtree_end(items, parent)
        else:
            at = len(items)
        items.insert(at, {
            "id": iid,
            "text": _clean_text(op.get("text")),
            "done": bool(op.get("done", False)),
            "priority": _valid_priority(op.get("priority")),
            "level": level if at > 0 else 0,
        })
    elif kind == "set":
        idx = pos.get(oid)
        if idx is None:
            return
        it = items[idx]
        if "text" in op:
            it["text"] = _clean_text(op.get("text"))
        if "priority" in op:
            it["priority"] = _valid_priority(op.get("priority"))
        if "level" in op:
            it["level"] = _clamp_level(op.get("level")) if idx > 0 else 0
        if "done" in op:
            done = bool(op.get("done"))
            # Mencentang (atau membuka) item induk ikut berlaku untuk sub-item-nya.
            for j in range(idx, _subtree_end(items, idx)):
                items[j]["done"] = done
    elif kind == "remove":
        idx = pos.get(oid)
        if idx is None:
            return
        if items[idx]["level"] == 0:
            # Sub-item tidak ikut terhapus: naik menjadi item biasa.
            for j in range(idx + 1, _subtree_end(items, idx)):
                items[j]["level"] = 0
        del items[idx]
    elif kind == "move":
        idx = pos.get(oid)
        if idx is None:
            return
        end = _subtree_end(items, idx)
        block = items[idx:end]
        del items[idx:end]
        moved = {it["id"] for it in block}
        before = _sid(op.get("before"))
        at = len(items)
        if before is not None and before not in moved:
            for i, it in enumerate(items):
                if it["id"] == before:
                    at = i
                    break
        level = _clamp_level(op.get("level", block[0]["level"]))
        block[0]["level"] = level if at > 0 else 0
        items[at:at] = block
    elif kind == "clear_done":
        out = []
        orphan = False  # item level 0 terdekat di atasnya ikut dibuang
        for it in items:
            if it["level"] == 0:
                orphan = it["done"]
            if it["done"]:
                continue
            if orphan and it["level"] > 0:
                it["level"] = 0
            out.append(it)
        items[:] = out


def _fix_levels(items: list[dict]) -> None:
    if items:
        items[0]["level"] = 0


def _checklist_of(note: dict) -> list[dict]:
    return _normalize_checklist(note.get("checklist"), keep_empty=True)


# ---------------------------------------------------------------------------
# Tugas berulang
# ---------------------------------------------------------------------------
def _add_month(d: date, day: int) -> date:
    y, m = (d.year + 1, 1) if d.month == 12 else (d.year, d.month + 1)
    return date(y, m, min(day, calendar.monthrange(y, m)[1]))


def next_due(due: Optional[str], recurrence: str, anchor_day: Optional[int] = None) -> Optional[str]:
    """Tenggat berikutnya setelah hari ini. Jam (bila ada) dipertahankan; bulanan memakai
    tanggal acuan agar 31 Jan -> 28/29 Feb -> 31 Mar, bukan bergeser ke 28 terus.
    None bila tidak bisa maju lagi (tenggat di ujung kalender, mis. tahun 9999)."""
    s = str(due or "").strip()
    date_part, _, time_part = s.partition("T")
    today = _now().date()
    try:
        d = date.fromisoformat(date_part)
    except ValueError:
        d, time_part = today, ""
    day = anchor_day if anchor_day and 1 <= anchor_day <= 31 else d.day
    try:
        if recurrence == "bulanan":
            while True:
                d = _add_month(d, day)
                if d > today:
                    break
        else:
            # Langsung ke jadwal pertama setelah hari ini (tenggat lama tidak dilangkahi satu per satu).
            step = _RECUR_DAYS[recurrence]
            d = d + timedelta(days=step * max(1, (today - d).days // step + 1))
    except (OverflowError, ValueError):
        return None
    return d.isoformat() + ("T" + time_part if time_part else "")


def _reactivate_recurring(n: dict) -> None:
    """Tugas berulang tidak pernah berstatus selesai (mis. pengulangan dipasang pada catatan
    yang sudah selesai, atau data dari versi lama): aktifkan lagi, tenggat lewat dimajukan."""
    if n.get("done") and _valid_recurrence(n.get("recurrence")):
        due_dt = _parse_due(n.get("due"))
        if due_dt is None or due_dt < _now():
            n["due"] = next_due(n.get("due"), n["recurrence"], n.get("recur_day")) or n.get("due")
        n["done"] = False


def _sync_recurrence(n: dict) -> None:
    """Dipanggil saat tenggat/pengulangan diubah pengguna: tugas berulang wajib bertenggat."""
    if n.get("recurrence"):
        if _parse_due(n.get("due")) is None:
            n["due"] = _now().date().isoformat()
        n["recur_day"] = _parse_due(n["due"]).day
    else:
        n["recur_day"] = None


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
    lead = min(max(_to_int(note.get("remind_before_days"), config.REMINDER_DEFAULT_LEAD_DAYS), 0), 3650)
    period = _RECUR_DAYS.get(note.get("recurrence") or "")
    if period:
        # Pengingat H-7 pada tugas harian/mingguan membuatnya selalu "akan datang".
        lead = min(lead, period - 1)
    try:
        soon = now >= (due_dt - timedelta(days=lead))
    except OverflowError:  # tenggat di tahun 1 (salah ketik) dikurangi H-n
        soon = True
    return "soon" if soon else "scheduled"


def _annotate(note: dict) -> dict:
    m = dict(note)
    m["status"] = compute_status(note)
    m.setdefault("category", config.DEFAULT_NOTE_CATEGORY)
    m["priority"] = _valid_priority(note.get("priority"))
    m["recurrence"] = _valid_recurrence(note.get("recurrence"))
    m["archived"] = bool(note.get("archived"))
    items = _checklist_of(note)
    m["checklist"] = items
    filled = [it for it in items if it["text"]]
    m["checklist_total"] = len(filled)
    m["checklist_done"] = sum(1 for it in filled if it["done"])
    return m


def _sort_key(note: dict):
    done = 1 if note.get("done") else 0
    pinned = 0 if note.get("pinned") else 1
    rank = _STATUS_ORDER.get(note.get("status", "none"), 4)
    prio = _PRIORITY_RANK.get(note.get("priority") or "", len(_PRIORITY_RANK))
    due_dt = _parse_due(note.get("due"))
    due_rank = due_dt or datetime.max
    return (done, pinned, rank, prio, due_rank, note.get("created_at", ""))


# ---------------------------------------------------------------------------
# Urungkan
# ---------------------------------------------------------------------------
def _prune_undo() -> None:
    limit = time.monotonic() - config.NOTE_UNDO_SECONDS
    for k in [k for k, v in _UNDO.items() if v["at"] < limit]:
        _UNDO.pop(k, None)


def _remember(note_id: str, kind: str, **payload: Any) -> None:
    _prune_undo()
    _UNDO[note_id] = {"kind": kind, "at": time.monotonic(), **payload}


# ---------------------------------------------------------------------------
# Operasi publik
# ---------------------------------------------------------------------------
def list_notes() -> list[dict]:
    """Catatan aktif (tanpa arsip)."""
    return [_annotate(n) for n in _read_raw() if not n.get("archived")]


def list_notes_sorted() -> list[dict]:
    return sorted(list_notes(), key=_sort_key)


def list_archived() -> list[dict]:
    """Catatan terarsip, yang terakhir diarsipkan di atas."""
    items = [_annotate(n) for n in _read_raw() if n.get("archived")]
    return sorted(items, key=lambda n: n.get("archived_at") or "", reverse=True)


def get_note(note_id: str) -> Optional[dict]:
    for n in _read_raw():
        if n.get("id") == note_id:
            return _annotate(n)
    return None


def add_note(data: dict) -> dict:
    now_iso = _now_iso()
    note = {
        "id": uuid.uuid4().hex,
        "title": (data.get("title") or "").strip(),
        "body": (data.get("body") or "").strip(),
        "tags": _normalize_tags(data.get("tags")),
        "category": _valid_category(data.get("category")),
        "priority": _valid_priority(data.get("priority")),
        "pinned": bool(data.get("pinned", False)),
        "done": bool(data.get("done", False)),
        "due": ((data.get("due") or "").strip() or None),
        "remind_before_days": _to_int(
            data.get("remind_before_days"), config.REMINDER_DEFAULT_LEAD_DAYS
        ),
        "recurrence": _valid_recurrence(data.get("recurrence")),
        "checklist": _normalize_checklist(data.get("checklist")),
        "archived": False,
        "archived_at": None,
        "created_at": now_iso,
        "updated_at": now_iso,
    }
    _sync_recurrence(note)
    _reactivate_recurring(note)
    with _LOCK:
        notes = _read_raw(strict=True)
        notes.append(note)
        _write_raw(notes)
    return _annotate(note)


def update_note(note_id: str, data: dict) -> Optional[dict]:
    with _LOCK:
        notes = _read_raw(strict=True)
        for n in notes:
            if n.get("id") != note_id:
                continue
            now_iso = _now_iso()
            if "title" in data:
                n["title"] = (data.get("title") or "").strip()
            if "body" in data:
                n["body"] = (data.get("body") or "").strip()
            if "tags" in data:
                n["tags"] = _normalize_tags(data.get("tags"))
            if "category" in data:
                n["category"] = _valid_category(data.get("category"))
            if "priority" in data:
                n["priority"] = _valid_priority(data.get("priority"))
            if "pinned" in data:
                n["pinned"] = bool(data.get("pinned"))
            if "due" in data:
                n["due"] = (data.get("due") or "").strip() or None
            if "remind_before_days" in data:
                n["remind_before_days"] = _to_int(
                    data.get("remind_before_days"), config.REMINDER_DEFAULT_LEAD_DAYS
                )
            if "recurrence" in data:
                n["recurrence"] = _valid_recurrence(data.get("recurrence"))
            if "due" in data or "recurrence" in data:
                _sync_recurrence(n)
            if "checklist" in data:
                n["checklist"] = _normalize_checklist(data.get("checklist"))
            if "archived" in data:
                archived = bool(data.get("archived"))
                if archived != bool(n.get("archived")):
                    _remember(note_id, "fields", fields={
                        "archived": bool(n.get("archived")), "archived_at": n.get("archived_at")})
                    n["archived"] = archived
                    n["archived_at"] = now_iso if archived else None
            recurred = False
            if "done" in data:
                done = bool(data.get("done"))
                if done and not n.get("done") and _valid_recurrence(n.get("recurrence")):
                    recurred = _complete_recurring(note_id, n, data, now_iso)
                else:
                    n["done"] = done
            _reactivate_recurring(n)
            n["updated_at"] = now_iso
            _write_raw(notes)
            result = _annotate(n)
            if recurred:
                result["recurred"] = True
            return result
    return None


def _complete_recurring(note_id: str, n: dict, data: dict, now_iso: str) -> bool:
    """Tugas berulang tidak pernah berstatus selesai: tenggat maju ke jadwal berikutnya dan
    centang checklist direset (pilihan pemilik, v1.4). Dipanggil sambil memegang _LOCK.

    Klik ganda atau tampilan basi tidak boleh melompati satu periode: tenggat hanya maju bila
    klien melihat tenggat yang sama (expect_due) dan tidak dua kali dalam 3 detik.
    """
    if "expect_due" in data and ((str(data.get("expect_due") or "").strip() or None) != (n.get("due") or None)):
        return False
    try:
        if 0 <= (_now() - datetime.fromisoformat(n.get("last_done_at") or "")).total_seconds() < 3:
            return False
    except ValueError:
        pass
    nxt = next_due(n.get("due"), n["recurrence"], n.get("recur_day"))
    if nxt is None:
        return False
    items = _checklist_of(n)
    _remember(note_id, "fields",
              fields={"due": n.get("due"), "last_done_at": n.get("last_done_at")},
              checks={it["id"]: it["done"] for it in items})
    n["due"] = nxt
    n["last_done_at"] = now_iso
    for it in items:
        it["done"] = False
    n["checklist"] = items
    n["done"] = False
    return True


def apply_checklist_ops(note_id: str, ops: Any) -> Optional[dict]:
    """Terapkan operasi checklist pada daftar terbaru di berkas (bukan menimpa seluruh daftar),
    sehingga edit dari sticky dan dari halaman Catatan tidak saling menimpa."""
    if not isinstance(ops, list):
        ops = []
    with _LOCK:
        notes = _read_raw(strict=True)
        for n in notes:
            if n.get("id") != note_id:
                continue
            items = _checklist_of(n)
            for op in ops[:500]:
                if isinstance(op, dict):
                    _apply_op(items, op)
            _fix_levels(items)
            n["checklist"] = items
            n["updated_at"] = _now_iso()
            _write_raw(notes)
            return _annotate(n)
    return None


def delete_note(note_id: str, extra: Any = None) -> bool:
    """Hapus catatan. `extra` (mis. status sticky) ikut dikembalikan bila diurungkan."""
    with _LOCK:
        notes = _read_raw(strict=True)
        for i, n in enumerate(notes):
            if n.get("id") == note_id:
                del notes[i]
                _write_raw(notes)
                _remember(note_id, "delete", note=n, extra=extra)
                return True
        return False


def undo(note_id: str) -> Optional[tuple[dict, Any]]:
    """Batalkan aksi terakhir (hapus/arsipkan/selesai-berulang) bila belum kedaluwarsa.

    Hasil: (catatan, extra) atau None. Hanya kolom yang diubah aksi itu yang dikembalikan,
    jadi edit lain sesudahnya (mis. dari sticky) tidak ikut hilang.
    """
    with _LOCK:
        _prune_undo()
        entry = _UNDO.get(note_id)
        if entry is None:
            return None
        # Entri baru dibuang setelah berhasil ditulis: berkas yang sedang terkunci (antivirus,
        # sinkronisasi) membuat permintaan gagal, tetapi Urungkan masih bisa dicoba lagi.
        notes = _read_raw(strict=True)
        current = next((n for n in notes if n.get("id") == note_id), None)
        if entry["kind"] == "delete":
            if current is not None:
                _UNDO.pop(note_id, None)
                return None
            current = dict(entry["note"])
            notes.append(current)
        else:
            if current is None:
                _UNDO.pop(note_id, None)
                return None
            current.update(entry.get("fields") or {})
            checks = entry.get("checks")
            if checks:
                items = _checklist_of(current)
                for it in items:
                    if it["id"] in checks:
                        it["done"] = checks[it["id"]]
                current["checklist"] = items
        current["updated_at"] = _now_iso()
        _write_raw(notes)
        _UNDO.pop(note_id, None)
        return _annotate(current), entry.get("extra")


def all_tags() -> list[str]:
    tags: list[str] = []
    for n in _read_raw():
        if n.get("archived"):
            continue
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
