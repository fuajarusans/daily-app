"""Desain 10 — Kop Surat: gaya surat resmi Indonesia dengan garis ganda di bawah kop."""
from app.invoice_designs._base import (
    BLACK, TEXT, Doc, InvoiceDesign, footer_section, items_table, meta, party, register_design,
)


@register_design
class KopSurat(InvoiceDesign):
    id = "kop-surat"
    name = "Kop Surat"
    description = "Gaya surat resmi Indonesia: kop bergaris ganda, terbilang dibingkai."
    order = 10

    def setup(self, d: Doc) -> None:
        d.set_margins(20, 15, 20)

    def render(self, d: Doc) -> None:
        c = d.ctx
        has_logo = d.logo(d.l_margin, 12, 26, 26, align="C") > 0
        x = d.l_margin + (30 if has_logo else 0)
        w = d.content_w - (60 if has_logo else 0)
        y = d.text_at(x, 13, w, (c.profile.get("name") or "").upper(), size=16, style="B",
                      color=BLACK, align="C") + 1
        y = d.lines_at(x, y, w, c.company_lines(), size=8.5, color=TEXT, align="C")
        y = max(y, 39 if has_logo else 0) + 2
        d.hline(y, BLACK, 0.9)
        d.hline(y + 1.3, BLACK, 0.25)

        d.font(14, "BU", color=BLACK)
        d.set_xy(d.l_margin, y + 6)
        d.cell(d.content_w, 7, "INVOICE", align="C")
        d.text_at(d.l_margin, y + 13.5, d.content_w, f"Nomor: {c.inv.get('number', '')}",
                  size=9.5, color=BLACK, align="C")

        y += 24
        y1 = party(d, d.l_margin, y, 95, "Kepada Yth.", c.client.get("name", ""),
                   c.client_lines(), title_color=TEXT, title_size=9, line_color=TEXT)
        y2 = meta(d, d.right - 68, y, 68, c.meta_rows()[1:], bold_value=False,
                  label_color=TEXT, label_w=24)
        d.set_y(max(y1, y2) + 7)

        items_table(d, head_fill=(240, 240, 240), line_color=BLACK, line_width=0.25)
        footer_section(d, terbilang_full=True,
                       totals_kw={"rule": BLACK, "label_color": TEXT},
                       terbilang_kw={"boxed": BLACK, "color": BLACK, "label_color": BLACK},
                       info_kw={"color": TEXT})
