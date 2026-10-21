"""Desain 3 — Minimalis: banyak ruang kosong, garis tipis, tipografi ringan."""
from app.invoice_designs._base import (
    BLACK, MUTED, Doc, InvoiceDesign, footer_section, items_table, party, register_design,
)

LIGHT = (225, 225, 225)


@register_design
class Minimalis(InvoiceDesign):
    id = "minimalis"
    name = "Minimalis"
    description = "Lega, garis tipis abu-abu, judul tipis besar."
    order = 3

    def setup(self, d: Doc) -> None:
        d.set_margins(20, 20, 20)

    def render(self, d: Doc) -> None:
        c = d.ctx
        d.font(34, "", "light", BLACK)
        d.set_xy(d.l_margin, 18)
        d.cell(100, 14, "Invoice")
        d.logo(d.right - 45, 18, 45, 16, align="R")

        y, col = 44, d.content_w / 3
        for i, (label, value) in enumerate(c.meta_rows()):
            x = d.l_margin + i * col
            d.text_at(x, y, col, label.upper(), size=7, color=MUTED)
            d.text_at(x, y + 4, col, value, size=9.5, color=BLACK)

        y = 64
        d.hline(y - 4, LIGHT, 0.2)
        half = (d.content_w - 10) / 2
        y1 = party(d, d.l_margin, y, half, "DARI", c.profile.get("name", ""),
                   c.company_lines(sep="\n"), title_size=7, name_size=10)
        y2 = party(d, d.l_margin + half + 10, y, half, "UNTUK", c.client.get("name", ""),
                   c.client_lines(sep="\n"), title_size=7, name_size=10)
        d.set_y(max(y1, y2) + 12)

        items_table(d, head_color=MUTED, head_bold=False, borders="HORIZONTAL_LINES",
                    line_color=LIGHT, head_size=7.5, head_upper=True, padding=2.6)
        footer_section(d, gap=8, totals_kw={"rule": LIGHT, "total_size": 14},
                       info_kw={"title_color": MUTED})
