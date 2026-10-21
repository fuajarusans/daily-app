"""Fondasi desain PDF invoice: registry desain, kanvas `Doc` (fpdf2), dan helper
blok-blok umum (identitas, tabel item, total, terbilang, pembayaran, catatan).

Tiap desain = satu file di folder ini berisi subclass `InvoiceDesign` dengan decorator
`@register_design` — otomatis dimuat (lihat `__init__.py`), pola sama dengan `tools/`.
Desain cukup menyusun helper di sini dengan gaya (warna, font, garis) berbeda.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from fpdf import FPDF, FontFace
from fpdf.enums import XPos, YPos

from app import invoice_format as fmt

RGB = tuple[int, int, int]

# fontTools mencetak peringatan tabel font yang tak bisa di-subset (tidak berbahaya).
logging.getLogger("fontTools.subset").setLevel(logging.ERROR)

BLACK: RGB = (25, 25, 25)
TEXT: RGB = (45, 45, 45)
MUTED: RGB = (115, 115, 115)
LINE: RGB = (200, 200, 200)
WHITE: RGB = (255, 255, 255)

# Font TrueType Windows (mendukung Unicode). Bila tidak ada, jatuh ke font inti
# fpdf (Helvetica/Times) dengan teks disaring ke Latin-1.
_FONT_DIR = Path("C:/Windows/Fonts")
_FONT_FILES = {
    "sans": {"": "arial.ttf", "B": "arialbd.ttf", "I": "ariali.ttf", "BI": "arialbi.ttf"},
    "serif": {"": "georgia.ttf", "B": "georgiab.ttf", "I": "georgiai.ttf", "BI": "georgiaz.ttf"},
    "light": {"": "segoeuil.ttf"},
}
_CORE = {"sans": "helvetica", "serif": "times", "light": "helvetica"}
_LATIN1_MAP = str.maketrans({"—": "-", "–": "-", "“": '"', "”": '"', "‘": "'", "’": "'", "…": "...", "•": "-"})


# ---------------------------------------------------------------------------
# Warna
# ---------------------------------------------------------------------------
def hex_rgb(value: str, fallback: str = "#333333") -> RGB:
    s = (value or fallback).lstrip("#")
    try:
        return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))
    except (ValueError, IndexError):
        return hex_rgb(fallback)


def tint(rgb: RGB, t: float) -> RGB:
    """Campur warna dengan putih (t=0 → warna asli, t=1 → putih)."""
    return tuple(int(c + (255 - c) * t) for c in rgb)  # type: ignore[return-value]


def shade(rgb: RGB, t: float) -> RGB:
    """Campur warna dengan hitam (t=0 → asli, t=1 → hitam)."""
    return tuple(int(c * (1 - t)) for c in rgb)  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Konteks data yang dirender
# ---------------------------------------------------------------------------
@dataclass
class Ctx:
    profile: dict
    inv: dict
    accent: RGB
    logo: Optional[Path]

    @property
    def totals(self) -> dict:
        return self.inv["totals"]

    @property
    def client(self) -> dict:
        return self.inv.get("client") or {}

    def company_lines(self, sep: str = "  ·  ") -> list[str]:
        p = self.profile
        lines = [ln for ln in (p.get("address") or "").splitlines() if ln.strip()]
        contact = sep.join(x for x in (p.get("phone"), p.get("email")) if x)
        if contact:
            lines.append(contact)
        if p.get("website"):
            lines.append(p["website"])
        if p.get("npwp"):
            lines.append(f"NPWP: {p['npwp']}")
        return lines

    def client_lines(self, sep: str = "  ·  ") -> list[str]:
        c = self.client
        lines = [ln for ln in (c.get("address") or "").splitlines() if ln.strip()]
        contact = sep.join(x for x in (c.get("phone"), c.get("email")) if x)
        if contact:
            lines.append(contact)
        if c.get("npwp"):
            lines.append(f"NPWP: {c['npwp']}")
        return lines

    def meta_rows(self) -> list[tuple[str, str]]:
        return [
            ("No. Invoice", self.inv.get("number", "")),
            ("Tanggal", fmt.tanggal(self.inv.get("date"))),
            ("Jatuh tempo", fmt.tanggal(self.inv.get("due_date"))),
        ]

    def total_rows(self) -> list[tuple[str, str]]:
        t, inv = self.totals, self.inv
        rows = [("Subtotal", fmt.rupiah(t["subtotal"]))]
        if t["discount"]:
            label = "Diskon"
            if inv.get("discount_type") == "percent":
                label += f" ({fmt.qty(inv.get('discount_value'))}%)"
            rows.append((label, "- " + fmt.rupiah(t["discount"])))
        if inv.get("tax_enabled"):
            rows.append((f"PPN ({fmt.qty(inv.get('tax_rate'))}%)", fmt.rupiah(t["tax"])))
        return rows


# ---------------------------------------------------------------------------
# Kanvas PDF
# ---------------------------------------------------------------------------
class Doc(FPDF):
    def __init__(self, ctx: Ctx):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.ctx = ctx
        self.decor = None          # callable(doc) — dekorasi tiap halaman (sidebar, dsb.)
        self.footer_color: RGB = MUTED
        self._families: dict[str, str] = {}
        self._unicode = True
        self._register_fonts()
        self.set_auto_page_break(True, margin=20)
        self.set_margins(15, 15, 15)
        self.set_title(f"Invoice {ctx.inv.get('number', '')}")
        self.set_author(ctx.profile.get("name") or "Daily App")
        self.set_creator("Daily App (Invoice Generator)")

    # --- font & teks ---
    def _register_fonts(self) -> None:
        for kind, files in _FONT_FILES.items():
            paths = {st: _FONT_DIR / fn for st, fn in files.items()}
            if not all(p.exists() for p in paths.values()):
                self._families[kind] = _CORE[kind]
                if kind != "light":
                    self._unicode = False
                continue
            fam = f"di_{kind}"
            for st, p in paths.items():
                self.add_font(fam, st, str(p))
            self._families[kind] = fam

    def font(self, size: float = 9.5, style: str = "", kind: str = "sans",
             color: Optional[RGB] = None) -> None:
        fam = self._families.get(kind, "helvetica")
        if kind == "light" and fam.startswith("di_"):
            style = ""  # Segoe UI Light hanya satu gaya
        self.set_font(fam, style, size)
        if color is not None:
            self.set_text_color(*color)

    def t(self, s: Any) -> str:
        s = "" if s is None else str(s)
        if self._unicode:
            return s
        return s.translate(_LATIN1_MAP).encode("latin-1", "replace").decode("latin-1")

    # --- hook halaman ---
    def header(self) -> None:
        if self.decor:
            self.decor(self)

    def footer(self) -> None:
        if self.ctx.inv.get("is_sample"):
            # Contoh PDF memakai kop & rekening asli brand: tandai jelas agar tak
            # tertukar dengan invoice sungguhan. Digambar terakhir (di atas sel tabel
            # yang berlatar putih) dengan transparansi supaya isi tetap terbaca.
            with self.local_context(fill_opacity=0.13), self.rotation(35, self.w / 2, self.h / 2):
                self.font(110, "B", color=(120, 120, 120))
                self.set_xy(0, self.h / 2 - 25)
                self.cell(self.w, 50, "CONTOH", align="C")
        self.set_y(-12)
        self.font(7, color=self.footer_color)
        self.cell(0, 4, self.t(f"{self.ctx.inv.get('number', '')}  ·  Halaman {self.page_no()}/{{nb}}"),
                  align="R")

    # --- primitif ---
    def fill(self, rgb: RGB) -> None:
        self.set_fill_color(*rgb)

    def draw(self, rgb: RGB, width: float = 0.2) -> None:
        self.set_draw_color(*rgb)
        self.set_line_width(width)

    def hline(self, y: float, rgb: RGB = LINE, width: float = 0.2,
              x1: Optional[float] = None, x2: Optional[float] = None) -> None:
        self.draw(rgb, width)
        self.line(self.l_margin if x1 is None else x1, y,
                  self.w - self.r_margin if x2 is None else x2, y)

    def text_at(self, x: float, y: float, w: float, text: str, size: float = 9.5,
                style: str = "", kind: str = "sans", color: RGB = TEXT,
                align: str = "L", lh: Optional[float] = None) -> float:
        """Tulis teks (boleh multi-baris) di kotak lebar w; kembalikan y akhir."""
        if not text:
            return y
        self.font(size, style, kind, color)
        self.set_xy(x, y)
        self.multi_cell(w, lh or size * 0.45, self.t(text), align=align,
                        new_x=XPos.LEFT, new_y=YPos.NEXT)
        return self.get_y()

    def lines_at(self, x: float, y: float, w: float, lines: list[str], size: float = 8.5,
                 color: RGB = MUTED, align: str = "L", kind: str = "sans") -> float:
        return self.text_at(x, y, w, "\n".join(lines), size=size, color=color,
                            align=align, kind=kind)

    def logo(self, x: float, y: float, w: float, h: float, align: str = "L") -> float:
        """Logo dimuat utuh di kotak (w×h) menjaga rasio. Kembalikan lebar terpakai (0 bila tak ada)."""
        path = self.ctx.logo
        if not path:
            return 0.0
        try:
            from PIL import Image
            with Image.open(path) as im:
                iw, ih = im.size
        except Exception:  # noqa: BLE001
            return 0.0
        scale = min(w / iw, h / ih)
        dw, dh = iw * scale, ih * scale
        dx = {"L": 0, "C": (w - dw) / 2, "R": w - dw}.get(align, 0)
        self.image(str(path), x=x + dx, y=y + (h - dh) / 2, w=dw, h=dh)
        return dw

    def ensure_space(self, h: float) -> None:
        if self.get_y() + h > self.page_break_trigger:
            self.add_page()

    @property
    def content_w(self) -> float:
        return self.w - self.l_margin - self.r_margin

    @property
    def right(self) -> float:
        return self.w - self.r_margin


# ---------------------------------------------------------------------------
# Blok umum
# ---------------------------------------------------------------------------
def party(d: Doc, x: float, y: float, w: float, title: str, name: str, lines: list[str],
          title_color: RGB = MUTED, name_color: RGB = BLACK, line_color: RGB = MUTED,
          kind: str = "sans", title_size: float = 7.5, name_size: float = 10.5,
          align: str = "L", line_size: float = 8.5) -> float:
    """Blok identitas: judul kecil, nama tebal, lalu baris-baris detail."""
    if title:
        y = d.text_at(x, y, w, title, size=title_size, style="B", color=title_color,
                      kind=kind, align=align) + 0.8
    y = d.text_at(x, y, w, name, size=name_size, style="B", color=name_color,
                  kind=kind, align=align) + 0.5
    return d.lines_at(x, y, w, lines, size=line_size, color=line_color, align=align, kind=kind)


def meta(d: Doc, x: float, y: float, w: float, rows: list[tuple[str, str]],
         label_w: float = 26, size: float = 9, label_color: RGB = MUTED,
         value_color: RGB = BLACK, kind: str = "sans", align_value: str = "R",
         bold_value: bool = True, row_h: float = 5) -> float:
    """Baris label–nilai (No. Invoice, Tanggal, Jatuh tempo)."""
    for label, value in rows:
        d.font(size, "", kind, label_color)
        d.set_xy(x, y)
        d.cell(label_w, row_h, d.t(label))
        d.font(size, "B" if bold_value else "", kind, value_color)
        d.cell(w - label_w, row_h, d.t(value), align=align_value)
        y += row_h
    return y


def col_widths(w: float) -> tuple[float, ...]:
    """Lebar kolom item: No · Deskripsi · Qty · Harga · Jumlah (skala ke lebar w)."""
    no, q, price, amount = (10.0, 24.0, 30.0, 32.0) if w >= 170 else (10.0, 20.0, 26.0, 29.0)
    return (no, w - (no + q + price + amount), q, price, amount)


def items_table(d: Doc, *, head_fill: Optional[RGB] = None, head_color: RGB = BLACK,
                head_bold: bool = True, borders: str = "ALL", line_color: RGB = LINE,
                line_width: float = 0.2, zebra: Optional[RGB] = None, size: float = 9,
                padding: float = 1.8, kind: str = "sans", body_color: RGB = TEXT,
                head_size: Optional[float] = None, head_upper: bool = False,
                gap_before: float = 0) -> float:
    """Tabel item (otomatis pindah halaman & mengulang judul kolom)."""
    ctx = d.ctx
    d.set_y(d.get_y() + gap_before)
    w = d.content_w
    heads = ["No", "Deskripsi", "Qty", "Harga", "Jumlah"]
    if head_upper:
        heads = [h.upper() for h in heads]
    d.draw(line_color, line_width)
    d.font(size, "", kind, body_color)
    # fpdf2 memakai warna fill aktif sebagai gaya dasar sel — reset agar warna blok
    # dekorasi (header/sidebar) tidak bocor ke baris tabel.
    d.fill(WHITE)
    head_style = FontFace(
        family=d._families.get(kind), emphasis="BOLD" if head_bold else None,
        color=head_color, fill_color=head_fill, size_pt=head_size or size,
    )
    aligns = ("CENTER", "LEFT", "CENTER", "RIGHT", "RIGHT")
    with d.table(
        width=w, col_widths=col_widths(w), text_align=aligns, align="LEFT",
        borders_layout=borders, headings_style=head_style,
        cell_fill_color=zebra, cell_fill_mode="ROWS" if zebra else "NONE",
        line_height=size * 0.48, padding=padding, first_row_as_headings=True,
    ) as table:
        row = table.row()
        for h in heads:
            row.cell(d.t(h))
        amounts = ctx.totals["line_amounts"]
        for i, it in enumerate(ctx.inv.get("items") or []):
            row = table.row()
            row.cell(str(i + 1))
            row.cell(d.t(it.get("desc", "")))
            unit = f" {it['unit']}" if it.get("unit") else ""
            row.cell(d.t(fmt.qty(it.get("qty")) + unit))
            row.cell(fmt.rupiah(it.get("price")))
            row.cell(fmt.rupiah(amounts[i] if i < len(amounts) else 0))
    return d.get_y()


def totals(d: Doc, x: float, y: float, w: float, *, size: float = 9, kind: str = "sans",
           label_color: RGB = MUTED, value_color: RGB = BLACK, row_h: float = 6,
           total_fill: Optional[RGB] = None, total_color: RGB = BLACK,
           total_size: float = 11, total_label: str = "Total", rule: Optional[RGB] = LINE,
           rule_width: float = 0.3, double_rule: bool = False, row_lines: Optional[RGB] = None,
           radius: float = 0) -> float:
    """Blok rincian total di kanan. Kembalikan y akhir."""
    pad = 2
    for label, value in d.ctx.total_rows():
        d.font(size, "", kind, label_color)
        d.set_xy(x + pad, y)
        d.cell(w / 2, row_h, d.t(label))
        d.font(size, "", kind, value_color)
        d.cell(w / 2 - 2 * pad, row_h, d.t(value), align="R")
        y += row_h
        if row_lines:
            d.hline(y, row_lines, 0.15, x, x + w)
    y += 1
    if rule and not total_fill:
        d.hline(y, rule, rule_width, x, x + w)
        if double_rule:
            d.hline(y + 1, rule, rule_width, x, x + w)
            y += 1
    th = row_h + 3
    if total_fill:
        d.fill(total_fill)
        if radius:
            d.rect(x, y, w, th, style="F", round_corners=True, corner_radius=radius)
        else:
            d.rect(x, y, w, th, style="F")
    d.font(total_size, "B", kind, total_color)
    d.set_xy(x + pad, y)
    d.cell(w * 0.4, th, d.t(total_label))
    d.cell(w * 0.6 - 2 * pad, th, d.t(fmt.rupiah(d.ctx.totals["total"])), align="R")
    return y + th


def terbilang(d: Doc, x: float, y: float, w: float, *, size: float = 8.5, kind: str = "sans",
              color: RGB = TEXT, label_color: RGB = MUTED, boxed: Optional[RGB] = None,
              box_fill: Optional[RGB] = None) -> float:
    text = d.ctx.totals["terbilang"]
    text = text[0].upper() + text[1:]
    if boxed or box_fill:
        # Ukur tinggi dulu agar kotak pas membungkus teks.
        d.font(size, "I", kind)
        lines = d.multi_cell(w - 4, size * 0.45, d.t(f"# {text} #"), dry_run=True, output="LINES")
        h = len(lines) * size * 0.45 + 6 + size * 0.45
        if box_fill:
            d.fill(box_fill)
        if boxed:
            d.draw(boxed, 0.3)
        d.rect(x, y, w, h, style=("DF" if boxed and box_fill else "D" if boxed else "F"))
        y2 = d.text_at(x + 2, y + 2, w - 4, "Terbilang:", size=size - 1, style="B", color=label_color, kind=kind)
        d.text_at(x + 2, y2 + 0.5, w - 4, f"# {text} #", size=size, style="I", color=color, kind=kind)
        return y + h
    y = d.text_at(x, y, w, "Terbilang", size=size - 1, style="B", color=label_color, kind=kind) + 0.5
    return d.text_at(x, y, w, text, size=size, style="I", color=color, kind=kind)


def payment(d: Doc, x: float, y: float, w: float, *, size: float = 8.5, kind: str = "sans",
            title_color: RGB = BLACK, color: RGB = TEXT, title: str = "Pembayaran",
            include_due: bool = True) -> float:
    ctx = d.ctx
    banks = ctx.profile.get("banks") or []
    if not banks and not include_due:
        return y
    y = d.text_at(x, y, w, title, size=size, style="B", color=title_color, kind=kind) + 0.8
    lines = []
    if include_due:
        lines.append(f"Mohon dibayar sebelum {fmt.tanggal(ctx.inv.get('due_date'))}.")
    for b in banks:
        parts = [b.get("bank", ""), b.get("number", "")]
        line = " ".join(p for p in parts if p)
        if b.get("holder"):
            line += f" a.n. {b['holder']}"
        lines.append(line)
    return d.lines_at(x, y, w, lines, size=size, color=color, kind=kind)


def notes(d: Doc, x: float, y: float, w: float, *, size: float = 8.5, kind: str = "sans",
          title_color: RGB = BLACK, color: RGB = MUTED, title: str = "Catatan") -> float:
    text = (d.ctx.inv.get("notes") or "").strip()
    if not text:
        return y
    y = d.text_at(x, y, w, title, size=size, style="B", color=title_color, kind=kind) + 0.8
    return d.text_at(x, y, w, text, size=size, color=color, kind=kind)


def paid_stamp(d: Doc, x: float, y: float) -> None:
    """Cap 'LUNAS' miring bila invoice sudah dibayar."""
    if d.ctx.inv.get("status") != "paid":
        return
    green = (30, 140, 70)
    with d.rotation(12, x + 20, y + 7):
        d.draw(green, 0.8)
        d.rect(x, y, 40, 14, style="D", round_corners=True, corner_radius=2)
        d.font(16, "B", "sans", green)
        d.set_xy(x, y)
        d.cell(40, 14, "LUNAS", align="C")


def footer_section(d: Doc, *, totals_kw: Optional[dict] = None, terbilang_kw: Optional[dict] = None,
                   info_kw: Optional[dict] = None, totals_w: float = 82, gap: float = 6,
                   show_payment: bool = True, terbilang_full: bool = False) -> float:
    """Susunan standar setelah tabel: total (kanan) + terbilang (kiri), lalu
    pembayaran & catatan berdampingan. Dipakai sebagian besar desain."""
    totals_kw = totals_kw or {}
    terbilang_kw = terbilang_kw or {}
    info_kw = info_kw or {}
    d.ensure_space(55)
    y0 = d.get_y() + gap
    x_tot = d.right - totals_w
    left_w = d.content_w - totals_w - 8
    y_tot = totals(d, x_tot, y0, totals_w, **totals_kw)
    paid_stamp(d, d.l_margin + left_w - 45, y0 + 2)
    if terbilang_full:
        y_left = y0
        y = max(y_tot, y_left) + 5
        y = terbilang(d, d.l_margin, y, d.content_w, **terbilang_kw)
    else:
        y_left = terbilang(d, d.l_margin, y0, left_w, **terbilang_kw)
        y = max(y_tot, y_left)
    d.set_y(y + 7)
    d.ensure_space(25)
    y = d.get_y()
    half = (d.content_w - 10) / 2
    if show_payment:
        y1 = payment(d, d.l_margin, y, half, **info_kw)
        y2 = notes(d, d.l_margin + half + 10, y, half, **info_kw)
    else:
        y1 = y
        y2 = notes(d, d.l_margin, y, d.content_w, **info_kw)
    return max(y1, y2)


# ---------------------------------------------------------------------------
# Registry desain
# ---------------------------------------------------------------------------
class InvoiceDesign:
    id: str = ""
    name: str = ""
    description: str = ""
    order: int = 99
    default_color: str = "#333333"
    uses_accent: bool = False   # True = warna aksen bisa diubah pengguna

    def setup(self, d: Doc) -> None:
        """Atur margin / dekorasi halaman sebelum add_page()."""

    def render(self, d: Doc) -> None:
        raise NotImplementedError

    def to_dict(self) -> dict:
        return {
            "id": self.id, "name": self.name, "description": self.description,
            "default_color": self.default_color, "uses_accent": self.uses_accent,
        }


_DESIGNS: dict[str, InvoiceDesign] = {}


def register_design(cls: type[InvoiceDesign]) -> type[InvoiceDesign]:
    inst = cls()
    if not inst.id or inst.id in _DESIGNS:
        raise ValueError(f"Desain {cls.__name__}: id kosong/duplikat.")
    _DESIGNS[inst.id] = inst
    return cls


def get_design(design_id: str) -> Optional[InvoiceDesign]:
    return _DESIGNS.get(design_id)


def all_designs() -> list[InvoiceDesign]:
    return sorted(_DESIGNS.values(), key=lambda x: (x.order, x.name))
