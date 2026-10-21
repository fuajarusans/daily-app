"""Penyimpanan Invoice Generator: brand (profil perusahaan), klien tersimpan, dan invoice.

Semua tersimpan permanen di `data/invoices.json` (di luar area auto-cleanup), ditulis
atomik (tulis .tmp lalu os.replace) dan dilindungi lock — pola yang sama dengan
`notes_store.py`. Logo tiap brand disimpan terpisah di `data/invoice_assets/logo_<id>.png`.

Multi-brand: tiap brand punya identitas, rekening, logo, prefix nomor, dan default
(jatuh tempo, PPN, catatan, desain) sendiri. Klien dipakai bersama semua brand. Invoice
merujuk brand lewat `brand_id` — PDF selalu memakai data brand terbaru.

Nomor invoice otomatis berformat `001/INV/X/2026` (urut/prefix/bulan romawi/tahun);
urutan terpisah per brand dan reset setiap tahun.
"""
from __future__ import annotations

import copy
import json
import os
import re
import shutil
import threading
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from app import config
from app.invoice_format import parse_date, romawi, terbilang

_LOCK = threading.RLock()

LEGACY_LOGO_FILE = "logo.png"  # format lama (satu profil) — dimigrasi ke logo_<brand>.png
_NUMBER_RE = re.compile(r"^\s*(\d+)\s*/.*?/\s*(\d{4})\s*$")
_HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
_ID_RE = re.compile(r"^[0-9a-f]{32}$")


# ---------------------------------------------------------------------------
# Util
# ---------------------------------------------------------------------------
def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _s(value: Any, limit: int = 2000) -> str:
    return str(value if value is not None else "").strip()[:limit]


def _num(value: Any, default: float = 0.0) -> float:
    try:
        v = float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return default
    return v if v == v else default  # buang NaN


def _int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _color(value: Any) -> str:
    s = _s(value, 7)
    return s if _HEX_RE.match(s) else ""


def _date_str(value: Any, fallback: Optional[date] = None) -> str:
    d = parse_date(value) or fallback
    return d.isoformat() if d else ""


def _clean_prefix(value: Any) -> str:
    return re.sub(r"[/\s]+", "", _s(value, 20)) or config.INVOICE_DEFAULT_PREFIX


# ---------------------------------------------------------------------------
# Baca / tulis berkas (+ migrasi format lama satu-profil → multi-brand)
# ---------------------------------------------------------------------------
def _default_brand() -> dict:
    return {
        "id": "",
        "name": "",
        "address": "",
        "phone": "",
        "email": "",
        "website": "",
        "npwp": "",
        "banks": [],  # [{"bank": "BCA", "number": "123", "holder": "PT ..."}]
        "prefix": config.INVOICE_DEFAULT_PREFIX,
        "due_days": config.INVOICE_DEFAULT_DUE_DAYS,
        "tax_rate": config.INVOICE_DEFAULT_TAX_RATE,
        "notes": "",
        "design": config.INVOICE_DEFAULT_DESIGN,
        "accent_color": "",  # "" = warna bawaan desain
        "created_at": "",
    }


def _empty() -> dict:
    return {"brands": [], "default_brand_id": "", "clients": [], "invoices": []}


def _migrate_legacy(data: dict) -> dict:
    """Format lama `{"profile": {...}}` → profil menjadi brand pertama.

    Berkas lama dibackup dulu, logo lama dipindah ke nama per-brand, dan semua invoice
    lama ditautkan ke brand tersebut."""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = config.INVOICES_FILE.with_name(f"invoices.backup-{stamp}.json")
    shutil.copy2(config.INVOICES_FILE, backup)

    brand = _default_brand()
    brand.update({k: v for k, v in (data.get("profile") or {}).items() if k in brand})
    brand["id"] = uuid.uuid4().hex
    brand["created_at"] = _now_iso()
    if not brand["name"]:
        brand["name"] = "Brand utama"
    old_logo = config.INVOICE_ASSETS_DIR / LEGACY_LOGO_FILE
    if old_logo.exists():
        os.replace(old_logo, _logo_file(brand["id"]))

    invoices = list(data.get("invoices") or [])
    for inv in invoices:
        inv.setdefault("brand_id", brand["id"])
    return {
        "brands": [brand],
        "default_brand_id": brand["id"],
        "clients": list(data.get("clients") or []),
        "invoices": invoices,
    }


def _read() -> dict:
    config.ensure_dirs()
    if not config.INVOICES_FILE.exists():
        return _empty()
    try:
        data = json.loads(config.INVOICES_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return _empty()
    if not isinstance(data, dict):
        return _empty()
    if "brands" not in data and "profile" in data:
        with _LOCK:
            # Baca ulang di dalam lock: request lain mungkin sudah memigrasi duluan.
            data = json.loads(config.INVOICES_FILE.read_text(encoding="utf-8"))
            if "brands" not in data:
                data = _migrate_legacy(data)
                _write(data)
    brands = []
    for b in data.get("brands") or []:
        full = _default_brand()
        full.update(b)
        brands.append(full)
    default_id = data.get("default_brand_id") or ""
    if brands and default_id not in {b["id"] for b in brands}:
        default_id = brands[0]["id"]
    return {
        "brands": brands,
        "default_brand_id": default_id,
        "clients": list(data.get("clients") or []),
        "invoices": list(data.get("invoices") or []),
    }


def _write(data: dict) -> None:
    config.ensure_dirs()
    tmp = config.INVOICES_FILE.parent / (config.INVOICES_FILE.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, config.INVOICES_FILE)  # penggantian atomik


# ---------------------------------------------------------------------------
# Brand (profil perusahaan)
# ---------------------------------------------------------------------------
def _logo_file(brand_id: str) -> Path:
    return config.INVOICE_ASSETS_DIR / f"logo_{brand_id}.png"


def logo_path(brand_id: str) -> Optional[Path]:
    if not _ID_RE.match(brand_id or ""):
        return None
    p = _logo_file(brand_id)
    return p if p.exists() else None


def save_logo_target(brand_id: str) -> Optional[Path]:
    """Path tujuan simpan logo (None bila brand tidak ada)."""
    if not _ID_RE.match(brand_id or "") or _find_brand(_read(), brand_id) is None:
        return None
    return _logo_file(brand_id)


def _find_brand(db: dict, brand_id: str) -> Optional[dict]:
    return next((b for b in db["brands"] if b["id"] == brand_id), None)


def _with_meta(b: dict, db: dict) -> dict:
    m = dict(b)
    m["has_logo"] = logo_path(b["id"]) is not None
    m["is_default"] = b["id"] == db["default_brand_id"]
    m["invoice_count"] = sum(1 for i in db["invoices"] if i.get("brand_id") == b["id"])
    return m


def list_brands() -> list[dict]:
    db = _read()
    return [_with_meta(b, db) for b in db["brands"]]


def default_brand_id() -> str:
    return _read()["default_brand_id"]


def get_brand(brand_id: str = "") -> Optional[dict]:
    """Brand menurut id; id kosong/tidak dikenal → brand default (None bila belum ada)."""
    db = _read()
    b = _find_brand(db, brand_id) or _find_brand(db, db["default_brand_id"])
    return _with_meta(b, db) if b else None


def _apply_brand_fields(b: dict, data: dict) -> None:
    for key in ("name", "address", "phone", "email", "website", "npwp", "notes"):
        if key in data:
            b[key] = _s(data.get(key))
    if "prefix" in data:
        b["prefix"] = _clean_prefix(data.get("prefix"))
    if "due_days" in data:
        b["due_days"] = max(0, min(365, _int(data.get("due_days"), config.INVOICE_DEFAULT_DUE_DAYS)))
    if "tax_rate" in data:
        b["tax_rate"] = max(0.0, min(100.0, _num(data.get("tax_rate"), config.INVOICE_DEFAULT_TAX_RATE)))
    if "design" in data:
        b["design"] = _s(data.get("design"), 40) or config.INVOICE_DEFAULT_DESIGN
    if "accent_color" in data:
        b["accent_color"] = _color(data.get("accent_color"))
    if "banks" in data:
        banks = []
        for row in data.get("banks") or []:
            if not isinstance(row, dict):
                continue
            clean = {k: _s(row.get(k), 200) for k in ("bank", "number", "holder")}
            if any(clean.values()):
                banks.append(clean)
        b["banks"] = banks


def _validate_brand(db: dict, b: dict) -> Optional[str]:
    if not b["name"]:
        return "Nama brand wajib diisi."
    for other in db["brands"]:
        if other["id"] != b["id"] and other["prefix"].lower() == b["prefix"].lower():
            return (f"Prefix '{b['prefix']}' sudah dipakai brand '{other['name']}'. "
                    "Gunakan prefix lain agar nomor invoice antar-brand tidak tertukar.")
    return None


def add_brand(data: dict) -> tuple[Optional[dict], Optional[str]]:
    with _LOCK:
        db = _read()
        b = _default_brand()
        b["id"] = uuid.uuid4().hex
        b["created_at"] = _now_iso()
        _apply_brand_fields(b, data)
        err = _validate_brand(db, b)
        if err:
            return None, err
        db["brands"].append(b)
        if not db["default_brand_id"] or data.get("is_default"):
            db["default_brand_id"] = b["id"]
        _write(db)
        return _with_meta(b, db), None


def update_brand(brand_id: str, data: dict) -> tuple[Optional[dict], Optional[str]]:
    with _LOCK:
        db = _read()
        b = _find_brand(db, brand_id)
        if b is None:
            return None, "Brand tidak ditemukan."
        trial = copy.deepcopy(b)
        _apply_brand_fields(trial, data)
        err = _validate_brand(db, trial)
        if err:
            return None, err
        b.update(trial)
        if data.get("is_default"):
            db["default_brand_id"] = b["id"]
        _write(db)
        return _with_meta(b, db), None


def set_default_brand(brand_id: str) -> bool:
    with _LOCK:
        db = _read()
        if _find_brand(db, brand_id) is None:
            return False
        db["default_brand_id"] = brand_id
        _write(db)
        return True


def delete_brand(brand_id: str) -> Optional[str]:
    """Hapus brand. Ditolak bila masih punya invoice. Kembalikan pesan error atau None."""
    with _LOCK:
        db = _read()
        b = _find_brand(db, brand_id)
        if b is None:
            return "Brand tidak ditemukan."
        count = sum(1 for i in db["invoices"] if i.get("brand_id") == brand_id)
        if count:
            return (f"Brand '{b['name']}' masih dipakai {count} invoice. Hapus atau pindahkan "
                    "invoice tersebut ke brand lain terlebih dahulu.")
        db["brands"] = [x for x in db["brands"] if x["id"] != brand_id]
        if db["default_brand_id"] == brand_id:
            db["default_brand_id"] = db["brands"][0]["id"] if db["brands"] else ""
        _write(db)
    logo = logo_path(brand_id)
    if logo:
        logo.unlink(missing_ok=True)
    return None


# ---------------------------------------------------------------------------
# Klien tersimpan (dipakai bersama semua brand)
# ---------------------------------------------------------------------------
_CLIENT_FIELDS = ("name", "address", "phone", "email", "npwp")


def _clean_client(data: dict) -> dict:
    return {k: _s(data.get(k)) for k in _CLIENT_FIELDS}


def list_clients() -> list[dict]:
    return sorted(_read()["clients"], key=lambda c: (c.get("name") or "").lower())


def add_client(data: dict) -> dict:
    client = {"id": uuid.uuid4().hex, **_clean_client(data)}
    with _LOCK:
        db = _read()
        db["clients"].append(client)
        _write(db)
    return client


def update_client(client_id: str, data: dict) -> Optional[dict]:
    with _LOCK:
        db = _read()
        for c in db["clients"]:
            if c.get("id") == client_id:
                c.update(_clean_client(data))
                _write(db)
                return c
    return None


def delete_client(client_id: str) -> bool:
    with _LOCK:
        db = _read()
        remaining = [c for c in db["clients"] if c.get("id") != client_id]
        if len(remaining) == len(db["clients"]):
            return False
        db["clients"] = remaining
        _write(db)
        return True


# ---------------------------------------------------------------------------
# Penomoran & perhitungan
# ---------------------------------------------------------------------------
def _parse_number(number: str) -> Optional[tuple[int, int]]:
    """'001/INV/X/2026' → (1, 2026)."""
    m = _NUMBER_RE.match(number or "")
    return (int(m.group(1)), int(m.group(2))) if m else None


def _next_number(db: dict, brand: Optional[dict], inv_date: Any = None) -> str:
    """Nomor berikutnya untuk brand & tahun tanggal invoice (urutan per brand, reset tiap tahun)."""
    d = parse_date(inv_date) or date.today()
    brand_id = brand["id"] if brand else ""
    last = 0
    for inv in db["invoices"]:
        if inv.get("brand_id") != brand_id:
            continue
        parsed = _parse_number(inv.get("number", ""))
        if parsed and parsed[1] == d.year:
            last = max(last, parsed[0])
    prefix = (brand or {}).get("prefix") or config.INVOICE_DEFAULT_PREFIX
    return f"{last + 1:03d}/{prefix}/{romawi(d.month)}/{d.year}"


def next_number(inv_date: Any = None, brand_id: str = "") -> str:
    db = _read()
    brand = _find_brand(db, brand_id) or _find_brand(db, db["default_brand_id"])
    return _next_number(db, brand, inv_date)


def compute_totals(inv: dict) -> dict:
    """Hitung subtotal, diskon, PPN, total, dan terbilang (dibulatkan ke rupiah)."""
    subtotal = 0
    lines = []
    for it in inv.get("items") or []:
        amount = int(round(_num(it.get("qty")) * _num(it.get("price"))))
        subtotal += amount
        lines.append(amount)
    disc_type = inv.get("discount_type") or "none"
    disc_val = _num(inv.get("discount_value"))
    if disc_type == "percent":
        discount = round(subtotal * disc_val / 100)
    elif disc_type == "amount":
        discount = round(disc_val)
    else:
        discount = 0
    discount = max(0, min(discount, subtotal))
    dpp = subtotal - discount
    tax = round(dpp * _num(inv.get("tax_rate")) / 100) if inv.get("tax_enabled") else 0
    total = dpp + tax
    return {
        "line_amounts": lines,
        "subtotal": subtotal,
        "discount": discount,
        "dpp": dpp,
        "tax": tax,
        "total": total,
        "terbilang": terbilang(total),
    }


def _effective_status(inv: dict) -> str:
    if inv.get("status") == "paid":
        return "paid"
    due = parse_date(inv.get("due_date"))
    if due and due < date.today():
        return "overdue"
    return "unpaid"


def annotate(inv: dict) -> dict:
    m = copy.deepcopy(inv)
    m["totals"] = compute_totals(inv)
    m["effective_status"] = _effective_status(inv)
    return m


# ---------------------------------------------------------------------------
# Invoice
# ---------------------------------------------------------------------------
def _clean_invoice(data: dict, brand: dict) -> dict:
    """Normalisasi input form invoice (dipakai untuk simpan maupun pratinjau)."""
    inv_date = parse_date(data.get("date")) or date.today()
    due_default = inv_date + timedelta(days=_int(brand.get("due_days"), 14))
    items = []
    for it in data.get("items") or []:
        if not isinstance(it, dict):
            continue
        row = {
            "desc": _s(it.get("desc"), 1000),
            "qty": _num(it.get("qty"), 1.0),
            "unit": _s(it.get("unit"), 30),
            "price": _num(it.get("price")),
        }
        if row["desc"] or row["price"]:
            items.append(row)
    disc_type = data.get("discount_type")
    client = data.get("client") if isinstance(data.get("client"), dict) else {}
    return {
        "brand_id": brand["id"],
        "number": _s(data.get("number"), 60),
        "date": inv_date.isoformat(),
        "due_date": _date_str(data.get("due_date"), due_default),
        "client_id": _s(data.get("client_id"), 64),
        "client": _clean_client(client),
        "items": items,
        "discount_type": disc_type if disc_type in ("percent", "amount") else "none",
        "discount_value": max(0.0, _num(data.get("discount_value"))),
        "tax_enabled": bool(data.get("tax_enabled")),
        "tax_rate": max(0.0, min(100.0, _num(data.get("tax_rate"), brand.get("tax_rate", 11)))),
        "notes": _s(data.get("notes"), 4000),
        "design": _s(data.get("design"), 40) or brand.get("design") or config.INVOICE_DEFAULT_DESIGN,
        "accent_color": _color(data.get("accent_color")),
        "status": "paid" if data.get("status") == "paid" else "unpaid",
    }


def validate(inv: dict) -> Optional[str]:
    if not inv["client"]["name"]:
        return "Nama klien wajib diisi."
    if not inv["items"]:
        return "Tambahkan minimal satu item."
    if not inv["number"]:
        return "Nomor invoice wajib diisi."
    return None


_NO_BRAND = "Belum ada brand. Buat brand terlebih dahulu di tab Brand."


def _resolve_brand(db: dict, brand_id: Any) -> Optional[dict]:
    return _find_brand(db, _s(brand_id, 64)) or _find_brand(db, db["default_brand_id"])


def build_preview(data: dict) -> tuple[Optional[dict], Optional[str]]:
    """Invoice dari form (belum disimpan) untuk pratinjau PDF."""
    db = _read()
    brand = _resolve_brand(db, data.get("brand_id"))
    if brand is None:
        return None, _NO_BRAND
    inv = _clean_invoice(data, brand)
    if not inv["number"]:
        inv["number"] = _next_number(db, brand, inv["date"])
    return annotate(inv), None


def list_invoices() -> list[dict]:
    invs = [annotate(i) for i in _read()["invoices"]]
    return sorted(invs, key=lambda i: (i.get("date", ""), i.get("created_at", "")), reverse=True)


def get_invoice(inv_id: str) -> Optional[dict]:
    for i in _read()["invoices"]:
        if i.get("id") == inv_id:
            return annotate(i)
    return None


def _number_taken(invoices: list, brand_id: str, number: str, except_id: str = "") -> bool:
    key = number.replace(" ", "").lower()
    return any(
        i.get("id") != except_id
        and i.get("brand_id") == brand_id
        and i.get("number", "").replace(" ", "").lower() == key
        for i in invoices
    )


def save_invoice(data: dict, inv_id: str = "") -> tuple[Optional[dict], Optional[str]]:
    """Buat (inv_id kosong) atau perbarui invoice. Kembalikan (invoice, pesan_error)."""
    with _LOCK:
        db = _read()
        brand = _resolve_brand(db, data.get("brand_id"))
        if brand is None:
            return None, _NO_BRAND
        inv = _clean_invoice(data, brand)
        if not inv["number"]:
            inv["number"] = _next_number(db, brand, inv["date"])
        err = validate(inv)
        if err:
            return None, err
        if _number_taken(db["invoices"], brand["id"], inv["number"], inv_id):
            return None, f"Nomor invoice '{inv['number']}' sudah dipakai di brand '{brand['name']}'."
        now = _now_iso()
        if inv_id:
            for i, old in enumerate(db["invoices"]):
                if old.get("id") == inv_id:
                    inv.update(id=inv_id, created_at=old.get("created_at", now), updated_at=now)
                    inv["paid_at"] = old.get("paid_at") if inv["status"] == "paid" else None
                    if inv["status"] == "paid" and not inv["paid_at"]:
                        inv["paid_at"] = now
                    db["invoices"][i] = inv
                    break
            else:
                return None, "Invoice tidak ditemukan."
        else:
            inv.update(id=uuid.uuid4().hex, created_at=now, updated_at=now,
                       paid_at=now if inv["status"] == "paid" else None)
            db["invoices"].append(inv)
        _write(db)
    return annotate(inv), None


def set_status(inv_id: str, status: str) -> Optional[dict]:
    with _LOCK:
        db = _read()
        for inv in db["invoices"]:
            if inv.get("id") == inv_id:
                inv["status"] = "paid" if status == "paid" else "unpaid"
                inv["paid_at"] = _now_iso() if inv["status"] == "paid" else None
                inv["updated_at"] = _now_iso()
                _write(db)
                return annotate(inv)
    return None


def duplicate_invoice(inv_id: str) -> Optional[dict]:
    """Salin invoice (brand sama): nomor baru, tanggal hari ini, status belum lunas."""
    with _LOCK:
        db = _read()
        src = next((i for i in db["invoices"] if i.get("id") == inv_id), None)
        if src is None:
            return None
        brand = _resolve_brand(db, src.get("brand_id"))
        today = date.today()
        new = copy.deepcopy(src)
        now = _now_iso()
        new.update(
            id=uuid.uuid4().hex,
            brand_id=brand["id"] if brand else src.get("brand_id", ""),
            number=_next_number(db, brand, today),
            date=today.isoformat(),
            due_date=(today + timedelta(days=_int((brand or {}).get("due_days"), 14))).isoformat(),
            status="unpaid",
            paid_at=None,
            created_at=now,
            updated_at=now,
        )
        db["invoices"].append(new)
        _write(db)
    return annotate(new)


def delete_invoice(inv_id: str) -> bool:
    with _LOCK:
        db = _read()
        remaining = [i for i in db["invoices"] if i.get("id") != inv_id]
        if len(remaining) == len(db["invoices"]):
            return False
        db["invoices"] = remaining
        _write(db)
        return True


def sample_invoice(brand: Optional[dict] = None) -> dict:
    """Invoice contoh untuk pratinjau desain di galeri."""
    brand = brand or _default_brand()
    today = date.today()
    return annotate({
        "brand_id": brand.get("id", ""),
        "is_sample": True,
        "number": f"CONTOH/{brand.get('prefix') or 'INV'}/{romawi(today.month)}/{today.year}",
        "date": today.isoformat(),
        "due_date": (today + timedelta(days=_int(brand.get("due_days"), 14))).isoformat(),
        "client": {
            "name": "PT Contoh Klien Sejahtera",
            "address": "Jl. Sudirman No. 10\nJakarta Selatan 12190",
            "phone": "021-5550123",
            "email": "finance@contohklien.co.id",
            "npwp": "01.234.567.8-901.000",
        },
        "items": [
            {"desc": "Jasa desain logo & identitas visual", "qty": 1, "unit": "paket", "price": 3500000},
            {"desc": "Desain kemasan produk (3 varian)", "qty": 3, "unit": "desain", "price": 750000},
            {"desc": "Cetak kartu nama", "qty": 5, "unit": "box", "price": 85000},
        ],
        "discount_type": "percent",
        "discount_value": 5,
        "tax_enabled": True,
        "tax_rate": brand.get("tax_rate", 11),
        "notes": brand.get("notes") or "Terima kasih atas kepercayaan Anda.",
        "status": "unpaid",
    })
