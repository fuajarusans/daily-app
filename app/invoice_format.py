"""Format angka & tanggal gaya Indonesia untuk Invoice Generator.

Dipakai bersama oleh `invoice_store` (perhitungan) dan desain PDF.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Optional

BULAN = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
]
ROMAWI = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"]

_SATUAN = [
    "", "satu", "dua", "tiga", "empat", "lima",
    "enam", "tujuh", "delapan", "sembilan", "sepuluh", "sebelas",
]


def parse_date(value: Any) -> Optional[date]:
    try:
        return date.fromisoformat(str(value).strip()[:10])
    except (TypeError, ValueError):
        return None


def tanggal(value: Any) -> str:
    """'2026-10-08' → '8 Oktober 2026'. Nilai tak valid dikembalikan apa adanya."""
    d = parse_date(value)
    if d is None:
        return str(value or "")
    return f"{d.day} {BULAN[d.month - 1]} {d.year}"


def romawi(month: int) -> str:
    return ROMAWI[(int(month) - 1) % 12]


def angka(value: Any) -> str:
    """1500000 → '1.500.000' (dibulatkan ke rupiah terdekat)."""
    n = int(round(float(value or 0)))
    s = f"{abs(n):,}".replace(",", ".")
    return f"-{s}" if n < 0 else s


def rupiah(value: Any) -> str:
    """1500000 → 'Rp 1.500.000'."""
    return f"Rp {angka(value)}"


def qty(value: Any) -> str:
    """Kuantitas: 2 → '2', 1.5 → '1,5'."""
    v = float(value or 0)
    if v == int(v):
        return f"{int(v):,}".replace(",", ".")
    return f"{v:,.2f}".rstrip("0").rstrip(".").replace(",", "X").replace(".", ",").replace("X", ".")


def _terbilang(n: int) -> str:
    if n < 12:
        return _SATUAN[n]
    if n < 20:
        return f"{_SATUAN[n - 10]} belas"
    if n < 100:
        return f"{_SATUAN[n // 10]} puluh {_terbilang(n % 10)}".strip()
    if n < 200:
        return f"seratus {_terbilang(n - 100)}".strip()
    if n < 1000:
        return f"{_SATUAN[n // 100]} ratus {_terbilang(n % 100)}".strip()
    if n < 2000:
        return f"seribu {_terbilang(n - 1000)}".strip()
    for besar, nama in (
        (10**12, "triliun"), (10**9, "miliar"), (10**6, "juta"), (10**3, "ribu"),
    ):
        if n >= besar:
            return f"{_terbilang(n // besar)} {nama} {_terbilang(n % besar)}".strip()
    return ""


def terbilang(value: Any) -> str:
    """1500000 → 'satu juta lima ratus ribu rupiah'."""
    n = int(round(float(value or 0)))
    if n == 0:
        return "nol rupiah"
    teks = _terbilang(abs(n))
    return f"{'minus ' if n < 0 else ''}{teks} rupiah"
