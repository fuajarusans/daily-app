"""Desain 1 — Klasik: hitam-putih formal, kop di tengah, tabel bergaris penuh."""
from app.invoice_designs._base import (
    BLACK, MUTED, Doc, InvoiceDesign, footer_section, items_table, meta, party, register_design,
)


@register_design
class Klasik(InvoiceDesign):
    id = "klasik"
    name = "Klasik"
    description = "Hitam-putih formal, kop di tengah, tabel bergaris penuh."
    order = 1

    def render(self, d: Doc) -> None:
        c = d.ctx
        has_logo = d.logo(d.l_margin, 14, 32, 22) > 0
        x, w = (d.l_margin + 36, d.content_w - 72) if has_logo else (d.l_margin, d.content_w)
        y = d.text_at(x, 15, w, c.profile.get("name") or "Nama Perusahaan", size=15,
                      style="B", color=BLACK, align="C") + 1
        y = d.lines_at(x, y, w, c.company_lines(), size=8.5, align="C")
        y = max(y, 38 if has_logo else 0) + 3
        d.hline(y, BLACK, 0.6)
        d.hline(y + 1, BLACK, 0.2)

        d.font(16, "B", color=BLACK)
        d.set_char_spacing(3)
        d.set_xy(d.l_margin, y + 5)
        d.cell(d.content_w, 9, "INVOICE", align="C")
        d.set_char_spacing(0)

        y = y + 19
        y1 = party(d, d.l_margin, y, 95, "DITAGIHKAN KEPADA", c.client.get("name", ""),
                   c.client_lines())
        y2 = meta(d, d.right - 75, y, 75, c.meta_rows())
        d.set_y(max(y1, y2) + 6)

        items_table(d, head_fill=(235, 235, 235), line_color=BLACK, line_width=0.25)
        footer_section(d, totals_kw={"rule": BLACK}, info_kw={"color": MUTED})
